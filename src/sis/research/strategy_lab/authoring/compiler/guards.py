from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _reward_risk_ratio,
    _signal_timestamp,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.risk_controls import TemporalRules
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_stop_target_width_gate(
    row: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, Any]:
    stop_loss_bps = row.get("stop_loss_bps")
    take_profit_bps = row.get("take_profit_bps")
    min_stop = row.get("min_stop_loss_bps")
    max_stop = row.get("max_stop_loss_bps")
    min_take = row.get("min_take_profit_bps")
    max_take = row.get("max_take_profit_bps")

    if row.get("side") not in {"long", "short"}:
        return row

    if min_stop is not None and max_stop is not None and float(max_stop) < float(min_stop):
        raise StrategyAuthoringValidationError(
            "rules.exit.max_stop_loss_bps must be >= min_stop_loss_bps"
        )
    if min_take is not None and max_take is not None and float(max_take) < float(min_take):
        raise StrategyAuthoringValidationError(
            "rules.exit.max_take_profit_bps must be >= min_take_profit_bps"
        )

    if min_stop is not None or max_stop is not None:
        if stop_loss_bps is None:
            return _block_trade_row(row, spec=spec, block_reason="stop_loss_bps_missing")
        stop = float(stop_loss_bps)
        if min_stop is not None and stop < float(min_stop):
            return _block_trade_row(row, spec=spec, block_reason="stop_loss_bps_too_low")
        if max_stop is not None and stop > float(max_stop):
            return _block_trade_row(row, spec=spec, block_reason="stop_loss_bps_too_high")

    if min_take is not None or max_take is not None:
        if take_profit_bps is None:
            return _block_trade_row(row, spec=spec, block_reason="take_profit_bps_missing")
        take = float(take_profit_bps)
        if min_take is not None and take < float(min_take):
            return _block_trade_row(row, spec=spec, block_reason="take_profit_bps_too_low")
        if max_take is not None and take > float(max_take):
            return _block_trade_row(row, spec=spec, block_reason="take_profit_bps_too_high")

    return row


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
