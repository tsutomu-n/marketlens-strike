from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl

REQUIRED_TIME_ORDER_COLUMNS = {"ts_signal", "source_feature_ts", "source_quote_ts"}


def _as_datetime(value: Any, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"{field_name} must be datetime, ISO string, or null")


def check_signal_time_order(frame: pl.DataFrame) -> dict[str, Any]:
    missing = REQUIRED_TIME_ORDER_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Leakage check missing columns: {sorted(missing)}")

    feature_violations: list[str] = []
    quote_violations: list[str] = []
    for index, row in enumerate(frame.to_dicts()):
        signal_ts = _as_datetime(row.get("ts_signal"), field_name="ts_signal")
        feature_ts = _as_datetime(row.get("source_feature_ts"), field_name="source_feature_ts")
        quote_ts = _as_datetime(row.get("source_quote_ts"), field_name="source_quote_ts")
        signal_id = str(row.get("signal_id") or index)
        if signal_ts is None:
            raise ValueError("ts_signal must be present")
        if feature_ts is not None and feature_ts > signal_ts:
            feature_violations.append(signal_id)
        if quote_ts is not None and quote_ts > signal_ts:
            quote_violations.append(signal_id)

    if feature_violations:
        raise ValueError(f"feature_ts > signal_ts for signals: {feature_violations}")
    if quote_violations:
        raise ValueError(f"quote_ts > signal_ts for signals: {quote_violations}")

    return {
        "status": "pass",
        "checked_rows": frame.height,
        "feature_time_violations": 0,
        "quote_time_violations": 0,
    }
