from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from sis.crypto_perp.bars import CandleBar, interval_to_milliseconds
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z


class CandleQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interval: str
    checked_at: datetime
    bar_count: int
    gap_count: int
    duplicate_count: int
    non_final_count: int
    ohlc_error_count: int
    event_generation_allowed: bool
    reason_codes: list[str]

    @field_validator("checked_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("checked_at", value)

    @field_serializer("checked_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _ohlc_invalid(bar: CandleBar) -> bool:
    open_price = Decimal(bar.open)
    high = Decimal(bar.high)
    low = Decimal(bar.low)
    close = Decimal(bar.close)
    return high < max(open_price, close) or low > min(open_price, close) or high < low


def validate_candle_series(
    bars: Sequence[CandleBar],
    *,
    interval: str,
    checked_at: datetime | str | None = None,
) -> CandleQualityReport:
    interval_ms = interval_to_milliseconds(interval)
    checked = ensure_utc_aware(
        "checked_at",
        checked_at or datetime.now(timezone.utc).replace(microsecond=0),
    )
    sorted_bars = sorted(bars, key=lambda item: item.ts_open)
    timestamps = [int(item.ts_open.timestamp() * 1000) for item in sorted_bars]
    duplicate_count = len(timestamps) - len(set(timestamps))
    unique_timestamps = sorted(set(timestamps))
    gap_count = 0
    for previous, current in zip(unique_timestamps, unique_timestamps[1:]):
        delta = current - previous
        if delta > interval_ms:
            gap_count += (delta // interval_ms) - 1
    non_final_count = sum(1 for item in sorted_bars if not item.is_final)
    ohlc_error_count = sum(1 for item in sorted_bars if _ohlc_invalid(item))

    reason_codes: list[str] = []
    if gap_count:
        reason_codes.append("GAP_DETECTED")
    if duplicate_count:
        reason_codes.append("DUPLICATE_BAR")
    if non_final_count:
        reason_codes.append("NON_FINAL_BAR")
    if ohlc_error_count:
        reason_codes.append("INVALID_OHLC")

    return CandleQualityReport(
        interval=interval,
        checked_at=checked,
        bar_count=len(sorted_bars),
        gap_count=gap_count,
        duplicate_count=duplicate_count,
        non_final_count=non_final_count,
        ohlc_error_count=ohlc_error_count,
        event_generation_allowed=not reason_codes,
        reason_codes=reason_codes,
    )
