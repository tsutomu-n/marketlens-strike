from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _signal_timestamp,
)
from sis.research.strategy_lab.authoring.compiler.reward_risk import _reward_risk_ratio
from sis.research.strategy_lab.authoring.compiler.stop_target_width import (
    _apply_stop_target_width_gate as _apply_stop_target_width_gate,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import TemporalRules
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_reward_risk_gate(row: dict[str, Any], spec: StrategyAuthoringSpec) -> dict[str, Any]:
    minimum = row.get("min_reward_risk_ratio")
    if minimum is None or row.get("side") not in {"long", "short"}:
        return row
    ratio = _reward_risk_ratio(row)
    row["min_reward_risk_ratio"] = minimum
    row["reward_risk_ratio"] = ratio
    if ratio is None:
        return _block_trade_row(row, spec=spec, block_reason="reward_risk_ratio_missing")
    if ratio < minimum:
        return _block_trade_row(row, spec=spec, block_reason="reward_risk_ratio_too_low")
    return row


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


def _apply_temporal_selection(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if not spec.rules.temporal.enabled:
        return rows

    last_signal_by_symbol: dict[str, datetime] = {}
    count_by_symbol_day: dict[tuple[str, object], int] = {}
    selected: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"])):
        if row.get("side") == "none":
            selected.append(row)
            continue
        reason = _temporal_block_reason(
            row,
            spec.rules.temporal,
            last_signal_by_symbol=last_signal_by_symbol,
            count_by_symbol_day=count_by_symbol_day,
        )
        if reason is not None:
            selected.append(_block_trade_row(row, spec=spec, block_reason=reason))
            continue

        ts_signal = _signal_timestamp(row)
        symbol = str(row["execution_symbol"])
        last_signal_by_symbol[symbol] = ts_signal
        day_key = (symbol, ts_signal.date())
        count_by_symbol_day[day_key] = count_by_symbol_day.get(day_key, 0) + 1
        selected.append(row)
    return selected
