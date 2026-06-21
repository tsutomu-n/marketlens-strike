from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


UNIVERSE_SCHEMA_VERSION = "crypto_perp_universe_snapshot.v1"
INSTRUMENT_METADATA_FIELDS = [
    "type",
    "launch_time",
    "off_time",
    "limit_open_time",
    "maker_fee_rate",
    "taker_fee_rate",
    "price_precision",
    "quantity_precision",
    "price_multiplier",
    "quantity_multiplier",
    "min_order_qty",
    "min_order_amount",
    "max_market_order_qty",
    "min_leverage",
    "max_leverage",
    "funding_interval_hours",
]


class UniverseSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    schema_version: str


class UniverseInstrument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_symbol: str
    canonical_symbol: str
    base_asset: str
    quote_asset: str
    type: str
    status: str
    launch_time: str
    off_time: str
    limit_open_time: str
    maker_fee_rate: str
    taker_fee_rate: str
    price_precision: str
    quantity_precision: str
    price_multiplier: str
    quantity_multiplier: str
    min_order_qty: str
    min_order_amount: str
    max_market_order_qty: str
    min_leverage: str
    max_leverage: str
    funding_interval_hours: str
    metadata_hash: str


class UniverseEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_symbol: str
    eligible_for_screening: bool
    eligible_for_measurement: bool
    liquidity_band: str
    reason_codes: list[str]


class UniverseStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_symbol: str
    previous: str
    current: str


class UniverseMetadataChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_symbol: str
    changed_fields: list[str]


class UniverseDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    added: list[str]
    removed: list[str]
    status_changed: list[UniverseStatusChange]
    metadata_changed: list[UniverseMetadataChange]


class UniverseSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_universe_snapshot.v1"] = UNIVERSE_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[UniverseSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    snapshot_id: str
    provider_id: Literal["bitget"]
    product_type: Literal["USDT-FUTURES"]
    observed_at: datetime
    response_complete: bool
    instruments: list[UniverseInstrument]
    eligibility: list[UniverseEligibility]
    diff: UniverseDiff

    @field_validator("created_at", "observed_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "observed_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _metadata_hash(row: Mapping[str, str]) -> str:
    return stable_hash(
        [
            "crypto-perp-instrument-metadata",
            {key: row.get(key, "") for key in INSTRUMENT_METADATA_FIELDS},
        ]
    )


def _instrument(row: Mapping[str, str]) -> UniverseInstrument:
    payload = dict(row)
    payload["metadata_hash"] = _metadata_hash(row)
    return UniverseInstrument.model_validate(payload)


def _instrument_by_symbol(
    instruments: Sequence[UniverseInstrument],
) -> dict[str, UniverseInstrument]:
    items: dict[str, UniverseInstrument] = {}
    for item in instruments:
        if item.native_symbol in items:
            raise ValueError(f"duplicate instrument symbol: {item.native_symbol}")
        items[item.native_symbol] = item
    return items


def _eligibility(
    instruments: Sequence[UniverseInstrument],
    *,
    quote_asset: str,
    require_online_status: bool,
) -> list[UniverseEligibility]:
    items: list[UniverseEligibility] = []
    for item in instruments:
        reason_codes: list[str] = []
        if item.quote_asset != quote_asset:
            reason_codes.append("QUOTE_ASSET_MISMATCH")
        if require_online_status and item.status != "online":
            reason_codes.append("STATUS_NOT_ONLINE")
        eligible = not reason_codes
        items.append(
            UniverseEligibility(
                native_symbol=item.native_symbol,
                eligible_for_screening=eligible,
                eligible_for_measurement=eligible,
                liquidity_band="UNKNOWN",
                reason_codes=reason_codes,
            )
        )
    return items


def _changed_fields(previous: UniverseInstrument, current: UniverseInstrument) -> list[str]:
    return sorted(
        field
        for field in INSTRUMENT_METADATA_FIELDS
        if getattr(previous, field) != getattr(current, field)
    )


def _diff(
    *,
    previous_snapshot: UniverseSnapshot | None,
    current_instruments: Sequence[UniverseInstrument],
    response_complete: bool,
) -> UniverseDiff:
    current_by_symbol = _instrument_by_symbol(current_instruments)
    previous_by_symbol = (
        _instrument_by_symbol(previous_snapshot.instruments)
        if previous_snapshot is not None
        else {}
    )
    added = sorted(symbol for symbol in current_by_symbol if symbol not in previous_by_symbol)
    removed = (
        sorted(symbol for symbol in previous_by_symbol if symbol not in current_by_symbol)
        if response_complete
        else []
    )
    status_changed: list[UniverseStatusChange] = []
    metadata_changed: list[UniverseMetadataChange] = []
    for symbol in sorted(set(current_by_symbol).intersection(previous_by_symbol)):
        previous = previous_by_symbol[symbol]
        current = current_by_symbol[symbol]
        if previous.status != current.status:
            status_changed.append(
                UniverseStatusChange(
                    native_symbol=symbol,
                    previous=previous.status,
                    current=current.status,
                )
            )
        fields = _changed_fields(previous, current)
        if fields:
            metadata_changed.append(
                UniverseMetadataChange(native_symbol=symbol, changed_fields=fields)
            )
    return UniverseDiff(
        added=added,
        removed=removed,
        status_changed=status_changed,
        metadata_changed=metadata_changed,
    )


def _snapshot_id(
    *,
    provider_id: str,
    product_type: str,
    observed_at: datetime,
    instruments: Sequence[UniverseInstrument],
) -> str:
    return stable_hash(
        [
            "crypto-perp-universe-snapshot",
            provider_id,
            product_type,
            serialize_utc_z(observed_at),
            [item.metadata_hash for item in instruments],
        ]
    )


def build_universe_snapshot(
    *,
    provider_id: Literal["bitget"],
    product_type: Literal["USDT-FUTURES"],
    observed_at: datetime | str,
    instruments: Sequence[Mapping[str, str]],
    previous_snapshot: UniverseSnapshot | None = None,
    response_complete: bool = True,
    quote_asset: str = "USDT",
    require_online_status: bool = True,
    source_refs: Sequence[Mapping[str, Any]] | None = None,
) -> UniverseSnapshot:
    observed = ensure_utc_aware("observed_at", observed_at)
    built_instruments = sorted(
        (_instrument(row) for row in instruments), key=lambda item: item.native_symbol
    )
    snapshot_id = _snapshot_id(
        provider_id=provider_id,
        product_type=product_type,
        observed_at=observed,
        instruments=built_instruments,
    )
    return UniverseSnapshot(
        artifact_id=stable_hash(["crypto-perp-universe-artifact", snapshot_id]),
        created_at=observed,
        producer=CryptoPerpProducer(command="crypto-perp-refresh"),
        source_refs=[UniverseSourceRef.model_validate(item) for item in source_refs or []],
        snapshot_id=snapshot_id,
        provider_id=provider_id,
        product_type=product_type,
        observed_at=observed,
        response_complete=response_complete,
        instruments=built_instruments,
        eligibility=_eligibility(
            built_instruments,
            quote_asset=quote_asset,
            require_online_status=require_online_status,
        ),
        diff=_diff(
            previous_snapshot=previous_snapshot,
            current_instruments=built_instruments,
            response_complete=response_complete,
        ),
    )
