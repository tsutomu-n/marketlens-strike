from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z


CandleType = Literal["market", "mark", "index", "premium"]


def interval_to_milliseconds(interval: str) -> int:
    if interval.endswith("m"):
        return int(interval.removesuffix("m")) * 60_000
    if interval.endswith("h"):
        return int(interval.removesuffix("h")) * 3_600_000
    raise ValueError(f"unsupported candle interval: {interval}")


def _utc_from_millis(value: int | str) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).replace(microsecond=0)


def _candle_type(value: str) -> CandleType:
    if value not in {"market", "mark", "index", "premium"}:
        raise ValueError(f"unsupported candle_type: {value}")
    return cast(CandleType, value)


class CandleBar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: Literal["bitget"]
    native_symbol: str
    candle_type: CandleType
    interval: str
    ts_open: datetime
    open: str
    high: str
    low: str
    close: str
    base_volume: str
    quote_turnover: str
    is_final: bool
    ts_available: datetime
    ts_ingested: datetime
    source_payload_sha256: str
    revision_number: int = 0

    @field_validator("ts_open", "ts_available", "ts_ingested", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("ts_open", "ts_available", "ts_ingested")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class CandleHistoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_symbol: str
    candle_type: CandleType = "market"
    interval: str
    start_time_ms: int
    end_time_ms: int
    limit: int


class CandleHistoryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: Literal["bitget"]
    observed_at: datetime
    history_backfill_hours: int
    interval: str
    requests: list[CandleHistoryRequest]

    @field_validator("observed_at", mode="before")
    @classmethod
    def validate_observed_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("observed_at", value)

    @field_serializer("observed_at")
    def serialize_observed_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


def build_candle_bars(
    *,
    provider_id: Literal["bitget"],
    native_symbol: str,
    candle_rows: Sequence[Mapping[str, str]],
    ts_ingested: datetime | str,
    source_payload_sha256: str,
    now_ms: int | None = None,
) -> list[CandleBar]:
    now = (
        _utc_from_millis(now_ms)
        if now_ms is not None
        else datetime.now(timezone.utc).replace(microsecond=0)
    )
    ingested = ensure_utc_aware("ts_ingested", ts_ingested)
    bars: list[CandleBar] = []
    for row in candle_rows:
        interval = row["interval"]
        ts_open = _utc_from_millis(row["ts_open"])
        ts_available = ts_open + timedelta(milliseconds=interval_to_milliseconds(interval))
        bars.append(
            CandleBar(
                provider_id=provider_id,
                native_symbol=native_symbol,
                candle_type=_candle_type(row["candle_type"]),
                interval=interval,
                ts_open=ts_open,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                base_volume=row["base_volume"],
                quote_turnover=row["quote_turnover"],
                is_final=ts_available <= now,
                ts_available=ts_available,
                ts_ingested=ingested,
                source_payload_sha256=source_payload_sha256,
            )
        )
    return sorted(bars, key=lambda item: item.ts_open)


def build_candle_history_plan(
    *,
    native_symbols: Sequence[str],
    observed_at: datetime | str,
    history_backfill_hours: int,
    interval: str,
    page_limit: int,
    provider_id: Literal["bitget"] = "bitget",
) -> CandleHistoryPlan:
    if history_backfill_hours <= 0:
        raise ValueError("history_backfill_hours must be positive")
    if page_limit <= 0:
        raise ValueError("page_limit must be positive")
    observed = ensure_utc_aware("observed_at", observed_at)
    interval_ms = interval_to_milliseconds(interval)
    end_ms = int(observed.timestamp() * 1000)
    start_ms = end_ms - history_backfill_hours * 3_600_000
    page_span_ms = interval_ms * page_limit
    requests: list[CandleHistoryRequest] = []
    for symbol in sorted(set(native_symbols)):
        cursor = start_ms
        while cursor < end_ms:
            request_end = min(cursor + page_span_ms, end_ms)
            request_limit = max(1, (request_end - cursor) // interval_ms)
            requests.append(
                CandleHistoryRequest(
                    native_symbol=symbol,
                    interval=interval,
                    start_time_ms=cursor,
                    end_time_ms=request_end,
                    limit=request_limit,
                )
            )
            cursor = request_end
    return CandleHistoryPlan(
        provider_id=provider_id,
        observed_at=observed,
        history_backfill_hours=history_backfill_hours,
        interval=interval,
        requests=requests,
    )
