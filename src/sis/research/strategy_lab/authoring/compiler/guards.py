from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _reward_risk_ratio,
    _signal_timestamp,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _non_negative_value,
    _optional_float_from_row,
    _positive_integer_value,
    _sizing_value,
    _unit_interval_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.risk_controls import TemporalRules
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _parse_event_ts(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise StrategyAuthoringValidationError(
                f"Invalid event window timestamp value: {value!r}"
            ) from exc
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _event_window_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    if not spec.rules.event_windows:
        return None
    ts_value = row.get("ts")
    if not isinstance(ts_value, datetime):
        raise StrategyAuthoringValidationError(f"Unsupported event window ts value: {ts_value!r}")
    ts_signal = ts_value if ts_value.tzinfo is not None else ts_value.replace(tzinfo=timezone.utc)
    for event_window in spec.rules.event_windows:
        event_ts = _parse_event_ts(row.get(event_window.event_ts_column))
        reason = event_window.block_reason or f"event_window_{event_window.name}"
        if event_ts is None:
            if event_window.mode == "allow":
                return f"{reason}_missing"
            continue
        start = event_ts - timedelta(minutes=event_window.before_minutes)
        end = event_ts + timedelta(minutes=event_window.after_minutes)
        in_window = start <= ts_signal <= end
        if event_window.mode == "allow" and not in_window:
            return f"{reason}_outside"
        if event_window.mode == "block" and in_window:
            return reason
    return None


def _risk_throttle_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    throttle = spec.rules.risk_throttle
    if not throttle.enabled:
        return None
    drawdown = _optional_float_from_row(row, throttle.max_drawdown_column)
    drawdown_floor = _sizing_value(
        row,
        fixed=throttle.max_drawdown_floor,
        column=throttle.max_drawdown_floor_column,
    )
    if drawdown is not None and drawdown_floor is not None and drawdown <= drawdown_floor:
        return "risk_throttle_max_drawdown"
    daily_loss = _optional_float_from_row(row, throttle.daily_loss_column)
    daily_loss_floor = _sizing_value(
        row,
        fixed=throttle.daily_loss_floor,
        column=throttle.daily_loss_floor_column,
    )
    if daily_loss is not None and daily_loss_floor is not None and daily_loss <= daily_loss_floor:
        return "risk_throttle_daily_loss"
    loss_streak = _optional_float_from_row(row, throttle.loss_streak_column)
    max_loss_streak = _positive_integer_value(
        row,
        fixed=throttle.max_loss_streak,
        column=throttle.max_loss_streak_column,
        field_name="rules.risk_throttle.max_loss_streak",
    )
    if loss_streak is not None and max_loss_streak is not None and loss_streak >= max_loss_streak:
        return "risk_throttle_loss_streak"
    return None


def _feature_timestamp(row: dict[str, Any]) -> datetime:
    ts = _parse_event_ts(row.get("ts"))
    if ts is None:
        raise StrategyAuthoringValidationError(f"Unsupported feature ts value: {row.get('ts')!r}")
    return ts


def _data_guard_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    guard = spec.rules.data_guard
    if not guard.enabled:
        return None
    feature_age = _optional_float_from_row(row, guard.feature_age_column)
    max_feature_age = _non_negative_value(
        row,
        fixed=guard.max_feature_age_minutes,
        column=guard.max_feature_age_minutes_column,
        field_name="rules.data_guard.max_feature_age_minutes",
    )
    if max_feature_age is not None:
        if feature_age is None:
            return "data_guard_feature_age_missing"
        if feature_age > max_feature_age:
            return "data_guard_feature_age_too_old"
    source_confidence = _optional_float_from_row(row, guard.source_confidence_column)
    min_source_confidence = _unit_interval_value(
        row,
        fixed=guard.min_source_confidence,
        column=guard.min_source_confidence_column,
        field_name="rules.data_guard.min_source_confidence",
    )
    if min_source_confidence is not None:
        if source_confidence is None:
            return "data_guard_source_confidence_missing"
        if source_confidence < min_source_confidence:
            return "data_guard_source_confidence_too_low"
    venue_quality = _optional_float_from_row(row, guard.venue_quality_score_column)
    min_venue_quality = _unit_interval_value(
        row,
        fixed=guard.min_venue_quality_score,
        column=guard.min_venue_quality_score_column,
        field_name="rules.data_guard.min_venue_quality_score",
    )
    if min_venue_quality is not None:
        if venue_quality is None:
            return "data_guard_venue_quality_missing"
        if venue_quality < min_venue_quality:
            return "data_guard_venue_quality_too_low"
    staleness_bps = _optional_float_from_row(row, guard.staleness_bps_column)
    max_staleness_bps = _non_negative_value(
        row,
        fixed=guard.max_staleness_bps,
        column=guard.max_staleness_bps_column,
        field_name="rules.data_guard.max_staleness_bps",
    )
    if max_staleness_bps is not None:
        if staleness_bps is None:
            return "data_guard_staleness_missing"
        if staleness_bps > max_staleness_bps:
            return "data_guard_staleness_too_high"
    regime_transition = _optional_float_from_row(row, guard.regime_transition_score_column)
    max_regime_transition = _non_negative_value(
        row,
        fixed=guard.max_regime_transition_score,
        column=guard.max_regime_transition_score_column,
        field_name="rules.data_guard.max_regime_transition_score",
    )
    if max_regime_transition is not None:
        if regime_transition is None:
            return "data_guard_regime_transition_missing"
        if regime_transition > max_regime_transition:
            return "data_guard_regime_transition_too_high"
    return None


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
