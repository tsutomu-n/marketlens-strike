from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_values import (
    _non_negative_value,
    _optional_float_from_row,
    _positive_integer_value,
    _sizing_value,
    _unit_interval_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
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
