from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.signal_timestamps import _signal_timestamp
from sis.research.strategy_lab.authoring.contracts.risk_controls import TemporalRules


def _temporal_block_reason(
    row: dict[str, Any],
    temporal: TemporalRules,
    *,
    last_signal_by_symbol: dict[str, datetime],
    count_by_symbol_day: dict[tuple[str, object], int],
) -> str | None:
    ts_signal = _signal_timestamp(row)
    if temporal.allowed_weekdays_utc is not None and ts_signal.weekday() not in set(
        temporal.allowed_weekdays_utc
    ):
        return "temporal_weekday_filter"
    if temporal.allowed_hours_utc is not None and ts_signal.hour not in set(
        temporal.allowed_hours_utc
    ):
        return "temporal_hour_filter"

    symbol = str(row["execution_symbol"])
    previous = last_signal_by_symbol.get(symbol)
    if (
        temporal.cooldown_minutes is not None
        and previous is not None
        and (ts_signal - previous).total_seconds() < temporal.cooldown_minutes * 60
    ):
        return "temporal_cooldown"

    day_key = (symbol, ts_signal.date())
    if (
        temporal.max_signals_per_symbol_per_day is not None
        and count_by_symbol_day.get(day_key, 0) >= temporal.max_signals_per_symbol_per_day
    ):
        return "temporal_symbol_daily_limit"
    return None
