from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from sis.crypto_perp.clock import ensure_utc_aware


CANDLE_AVAILABLE_BEFORE_BUCKET_CLOSE = "CANDLE_AVAILABLE_BEFORE_BUCKET_CLOSE"
CANDLE_TIMESTAMPS_NOT_UNIQUE = "CANDLE_TIMESTAMPS_NOT_UNIQUE"
CANDLE_TIMESTAMPS_NOT_STRICTLY_INCREASING = "CANDLE_TIMESTAMPS_NOT_STRICTLY_INCREASING"
CANDLE_OHLC_INVALID = "CANDLE_OHLC_INVALID"
CANDLE_VOLUME_INVALID = "CANDLE_VOLUME_INVALID"
LOOKBACK_CANDLES_NOT_CONTIGUOUS = "LOOKBACK_CANDLES_NOT_CONTIGUOUS"
LOOKBACK_CANDLE_NOT_AVAILABLE_BY_CUTOFF = "LOOKBACK_CANDLE_NOT_AVAILABLE_BY_CUTOFF"


def _finite_decimal(row: Mapping[str, str], field: str) -> Decimal:
    try:
        value = Decimal(row[field])
    except (KeyError, InvalidOperation, ValueError) as exc:
        raise ValueError(f"CANDLE_NUMERIC_FIELD_INVALID: {field}") from exc
    if not value.is_finite():
        raise ValueError(f"CANDLE_NUMERIC_FIELD_INVALID: {field}")
    return value


def validate_candle_rows(rows: Sequence[Mapping[str, str]], interval_minutes: int) -> None:
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")
    interval = timedelta(minutes=interval_minutes)
    timestamps = [ensure_utc_aware("ts", row["ts"]) for row in rows]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError(CANDLE_TIMESTAMPS_NOT_UNIQUE)
    if any(current <= previous for previous, current in zip(timestamps, timestamps[1:])):
        raise ValueError(CANDLE_TIMESTAMPS_NOT_STRICTLY_INCREASING)
    for row, timestamp in zip(rows, timestamps, strict=True):
        available_at = ensure_utc_aware("available_at", row["available_at"])
        if available_at < timestamp + interval:
            raise ValueError(
                f"{CANDLE_AVAILABLE_BEFORE_BUCKET_CLOSE}: "
                f"ts={row['ts']} available_at={row['available_at']}"
            )
        open_price = _finite_decimal(row, "open")
        high = _finite_decimal(row, "high")
        low = _finite_decimal(row, "low")
        close = _finite_decimal(row, "close")
        if (
            min(open_price, high, low, close) <= 0
            or high < max(open_price, close)
            or low > min(open_price, close)
        ):
            raise ValueError(f"{CANDLE_OHLC_INVALID}: ts={row['ts']}")
        for volume_field in ("base_vol", "quote_vol"):
            if volume_field in row and _finite_decimal(row, volume_field) < 0:
                raise ValueError(f"{CANDLE_VOLUME_INVALID}: ts={row['ts']} field={volume_field}")


def validate_signal_lookback_window(
    rows: Sequence[Mapping[str, str]],
    index: int,
    lookback_bars: int,
    interval_minutes: int,
) -> None:
    if lookback_bars <= 0:
        raise ValueError("lookback_bars must be positive")
    start = index - lookback_bars + 1
    if start < 0:
        raise ValueError(f"{LOOKBACK_CANDLES_NOT_CONTIGUOUS}: insufficient lookback rows")
    window = rows[start : index + 1]
    if len(window) != lookback_bars:
        raise ValueError(f"{LOOKBACK_CANDLES_NOT_CONTIGUOUS}: insufficient lookback rows")
    interval = timedelta(minutes=interval_minutes)
    cutoff = ensure_utc_aware("information_cutoff_at", rows[index]["available_at"])
    first_at = ensure_utc_aware("lookback_first_at", window[0]["ts"])
    for offset, row in enumerate(window):
        timestamp = ensure_utc_aware("lookback_row_at", row["ts"])
        if timestamp != first_at + interval * offset:
            raise ValueError(f"{LOOKBACK_CANDLES_NOT_CONTIGUOUS}: gap inside signal window")
        available_at = ensure_utc_aware("lookback_available_at", row["available_at"])
        if available_at > cutoff:
            raise ValueError(
                f"{LOOKBACK_CANDLE_NOT_AVAILABLE_BY_CUTOFF}: "
                f"ts={row['ts']} available_at={row['available_at']}"
            )
