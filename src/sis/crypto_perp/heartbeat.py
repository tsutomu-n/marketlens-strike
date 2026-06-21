from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    decimal_to_json_string,
    stable_hash,
)


MARKET_SNAPSHOT_SCHEMA_VERSION = "crypto_perp_market_snapshot.v1"


class MarketSnapshotSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    schema_version: str


class MarketTickerSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: Literal["bitget"]
    native_symbol: str
    ts_event: str
    ts_received: datetime
    last_price: str
    bid1_price: str
    ask1_price: str
    bid1_size: str
    ask1_size: str
    spread_bps: str
    price_change_24h: str
    volume_24h_base: str
    turnover_24h_quote: str
    index_price: str
    mark_price: str
    funding_rate: str
    open_interest_raw: str
    open_interest_unit: str
    source_payload_sha256: str

    @field_validator("ts_received", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("ts_received", value)

    @field_serializer("ts_received")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_market_snapshot.v1"] = MARKET_SNAPSHOT_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[MarketSnapshotSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    snapshot_id: str
    provider_id: Literal["bitget"]
    observed_at: datetime
    tickers: list[MarketTickerSnapshot]

    @field_validator("created_at", "observed_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "observed_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _spread_bps(*, bid: str, ask: str) -> str:
    bid_value = Decimal(bid)
    ask_value = Decimal(ask)
    if bid_value <= 0 or ask_value <= 0 or ask_value < bid_value:
        raise ValueError("invalid bid/ask for spread calculation")
    mid = (bid_value + ask_value) / Decimal("2")
    spread = (ask_value - bid_value) / mid * Decimal("10000")
    return decimal_to_json_string(spread.quantize(Decimal("0.00000001")))


def _ticker(
    *,
    provider_id: Literal["bitget"],
    observed_at: datetime,
    row: Mapping[str, str],
    source_payload_sha256: str,
) -> MarketTickerSnapshot:
    return MarketTickerSnapshot(
        provider_id=provider_id,
        native_symbol=row["native_symbol"],
        ts_event=row["ts_event"],
        ts_received=observed_at,
        last_price=row["last_price"],
        bid1_price=row["bid1_price"],
        ask1_price=row["ask1_price"],
        bid1_size=row["bid1_size"],
        ask1_size=row["ask1_size"],
        spread_bps=_spread_bps(bid=row["bid1_price"], ask=row["ask1_price"]),
        price_change_24h=row["price_change_24h"],
        volume_24h_base=row["volume_24h_base"],
        turnover_24h_quote=row["turnover_24h_quote"],
        index_price=row["index_price"],
        mark_price=row["mark_price"],
        funding_rate=row["funding_rate"],
        open_interest_raw=row["open_interest_raw"],
        open_interest_unit="base",
        source_payload_sha256=source_payload_sha256,
    )


def build_market_snapshot(
    *,
    provider_id: Literal["bitget"],
    observed_at: datetime | str,
    ticker_rows: Sequence[Mapping[str, str]],
    source_payload_sha256: str,
    source_refs: Sequence[Mapping[str, Any]] | None = None,
) -> MarketSnapshot:
    observed = ensure_utc_aware("observed_at", observed_at)
    tickers = sorted(
        (
            _ticker(
                provider_id=provider_id,
                observed_at=observed,
                row=row,
                source_payload_sha256=source_payload_sha256,
            )
            for row in ticker_rows
        ),
        key=lambda item: item.native_symbol,
    )
    snapshot_id = stable_hash(
        [
            "crypto-perp-market-snapshot",
            provider_id,
            serialize_utc_z(observed),
            [item.model_dump(mode="json") for item in tickers],
        ]
    )
    return MarketSnapshot(
        artifact_id=stable_hash(["crypto-perp-market-snapshot-artifact", snapshot_id]),
        created_at=observed,
        producer=CryptoPerpProducer(command="crypto-perp-refresh"),
        source_refs=[MarketSnapshotSourceRef.model_validate(item) for item in source_refs or []],
        snapshot_id=snapshot_id,
        provider_id=provider_id,
        observed_at=observed,
        tickers=tickers,
    )
