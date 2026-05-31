from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Iterable, Literal, cast

import polars as pl

from sis.research.signal_builder import _legacy_export
from sis.research.strategy_lab.authoring.confirmation import _apply_confirmation_panels
from sis.research.strategy_lab.authoring.contracts import (
    AuthoringRules,
    Condition,
    DEFAULT_EXIT_PRIORITY,
    EntryRules,
    PortfolioRules,
    RegimeOverride,
    ScoreRules,
    StrategyAuthoringSpec,
    StrategyAuthoringValidationError,
    TemporalRules,
    _stable_digest,
)
from sis.research.strategy_lab.authoring.features import (
    _apply_condition_features,
    _apply_derived_features,
    _condition_passes,
)
from sis.research.strategy_lab.authoring.validation import _resolve_path, validate_authoring_inputs
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    empty_signal_artifact_run_id,
    empty_strategy_signal_frame,
    file_sha256,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
    write_strategy_signal_manifest,
)
from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.specs import SymbolBinding
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord
from sis.backtest.signals import ResearchSignal


def _entry_passes(row: dict[str, Any], entry: EntryRules) -> bool:
    all_pass = all(_condition_passes(row, condition) for condition in entry.all)
    any_pass = (
        True if not entry.any else any(_condition_passes(row, condition) for condition in entry.any)
    )
    none_pass = not any(_condition_passes(row, condition) for condition in entry.none)
    return all_pass and any_pass and none_pass


def _score(row: dict[str, Any], score: ScoreRules) -> float | None:
    if not score.enabled:
        return None
    total = 0.0
    used = False
    for term in score.weighted_sum:
        value = row.get(term.column)
        if isinstance(value, int | float):
            total += float(value) * term.weight
            used = True
    if score.model_score is not None:
        model_total = score.model_score.intercept
        model_used = False
        for term in score.model_score.coefficients:
            value = row.get(term.column)
            if not isinstance(value, int | float) and score.model_score.missing_value is not None:
                value = score.model_score.missing_value
            if isinstance(value, int | float):
                model_total += float(value) * term.weight
                model_used = True
        if model_used:
            if score.model_score.activation == "sigmoid":
                if model_total >= 0:
                    z = math.exp(-model_total)
                    model_total = 1.0 / (1.0 + z)
                else:
                    z = math.exp(model_total)
                    model_total = z / (1.0 + z)
            elif score.model_score.activation == "tanh":
                model_total = math.tanh(model_total)
            elif score.model_score.activation == "clamp_0_1":
                model_total = max(0.0, min(1.0, model_total))
            total += model_total
            used = True
    return total if used else None


def _rank_score(raw_score: float | None) -> float | None:
    if raw_score is None:
        return None
    return max(0.0, min(1.0, raw_score))


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _tail_bucket(rank_score: float | None) -> str:
    if rank_score is None:
        return "none"
    if rank_score >= 0.8:
        return "top"
    if rank_score <= 0.2:
        return "bottom"
    return "middle"


def _optional_float_from_row(row: dict[str, Any], column: str | None) -> float | None:
    if column is None:
        return None
    value = row.get(column)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return None


def _exit_bps(row: dict[str, Any], *, fixed: float | None, column: str | None) -> float | None:
    dynamic = _optional_float_from_row(row, column)
    return dynamic if dynamic is not None else fixed


def _sizing_value(row: dict[str, Any], *, fixed: float | None, column: str | None) -> float | None:
    dynamic = _optional_float_from_row(row, column)
    return dynamic if dynamic is not None else fixed


def _non_negative_bps_value(
    row: dict[str, Any],
    *,
    fixed: float | None,
    column: str | None,
    field_name: str,
) -> float | None:
    value = _exit_bps(row, fixed=fixed, column=column)
    if value is not None and value < 0:
        raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
    return value


def _minutes_value(row: dict[str, Any], *, fixed: int | None, column: str | None) -> int | None:
    dynamic = _optional_float_from_row(row, column)
    if dynamic is None:
        return fixed
    if not float(dynamic).is_integer():
        raise StrategyAuthoringValidationError(f"{column} must be an integer minute value")
    return int(dynamic)


def _positive_integer_value(
    row: dict[str, Any],
    *,
    fixed: int | None,
    column: str | None,
    field_name: str,
) -> int | None:
    dynamic = _optional_float_from_row(row, column)
    value = fixed if dynamic is None else dynamic
    if value is None:
        return None
    if not float(value).is_integer():
        raise StrategyAuthoringValidationError(f"{field_name} must be an integer value")
    integer_value = int(value)
    if integer_value <= 0:
        raise StrategyAuthoringValidationError(f"{field_name} must be positive")
    return integer_value


def _non_negative_value(
    row: dict[str, Any],
    *,
    fixed: float | None,
    column: str | None,
    field_name: str,
) -> float | None:
    value = _sizing_value(row, fixed=fixed, column=column)
    if value is not None and value < 0:
        raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
    return value


def _unit_interval_value(
    row: dict[str, Any],
    *,
    fixed: float | None,
    column: str | None,
    field_name: str,
) -> float | None:
    value = _sizing_value(row, fixed=fixed, column=column)
    if value is not None and not 0.0 <= value <= 1.0:
        raise StrategyAuthoringValidationError(f"{field_name} must be between 0 and 1")
    return value


def _entry_type_value(
    row: dict[str, Any],
    *,
    fixed: Literal["market", "limit", "stop_market"],
    column: str | None,
) -> Literal["market", "limit", "stop_market"]:
    if column is None:
        return fixed
    value = row.get(column)
    if value is None or (isinstance(value, str) and not value.strip()):
        return fixed
    normalized = str(value).strip().lower()
    if normalized in {"market", "limit", "stop_market"}:
        return cast(Literal["market", "limit", "stop_market"], normalized)
    raise StrategyAuthoringValidationError(
        f"Unsupported rules.order.entry_type_column value: {value}"
    )


def _time_in_force_value(
    row: dict[str, Any],
    *,
    fixed: Literal["gtc", "gtd", "ioc", "fok"],
    column: str | None,
) -> Literal["gtc", "gtd", "ioc", "fok"]:
    if column is None:
        return fixed
    value = row.get(column)
    if value is None or (isinstance(value, str) and not value.strip()):
        return fixed
    normalized = str(value).strip().lower()
    if normalized in {"gtc", "gtd", "ioc", "fok"}:
        return cast(Literal["gtc", "gtd", "ioc", "fok"], normalized)
    raise StrategyAuthoringValidationError(
        f"Unsupported rules.order.time_in_force_column value: {value}"
    )


def _optional_bool_from_row(row: dict[str, Any], column: str | None) -> bool | None:
    if column is None:
        return None
    value = row.get(column)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise StrategyAuthoringValidationError(f"Unsupported boolean value in {column}: {value}")


def _matching_regime_override(
    row: dict[str, Any], spec: StrategyAuthoringSpec
) -> RegimeOverride | None:
    for regime in spec.rules.regime_overrides:
        if _entry_passes(row, regime.when):
            return regime
    return None


def _regime_value(
    regime: RegimeOverride | None, field_name: str, default: float | None
) -> float | None:
    if regime is None:
        return default
    value = getattr(regime, field_name)
    return value if value is not None else default


def _exit_override(
    overrides: dict[str, float | None] | None, field_name: str, default: float | None
) -> float | None:
    if overrides is None:
        return default
    value = overrides.get(field_name)
    return value if value is not None else default


def _exit_override_column(
    overrides: dict[str, float | None] | None, field_name: str, default: str | None
) -> str | None:
    if overrides is not None and field_name in overrides:
        return None
    return default


def _override_value(overrides: dict[str, Any] | None, field_name: str, default: Any) -> Any:
    if overrides is None:
        return default
    value = overrides.get(field_name)
    return value if value is not None else default


def _override_column(
    overrides: dict[str, Any] | None, field_name: str, default: str | None
) -> str | None:
    if overrides is not None and field_name in overrides:
        return None
    return default


def _signal_position_weight(row: dict[str, Any], spec: StrategyAuthoringSpec) -> float | None:
    regime = _matching_regime_override(row, spec)
    fixed = _regime_value(regime, "position_weight", spec.rules.sizing.position_weight)
    base = _sizing_value(row, fixed=fixed, column=spec.rules.sizing.position_weight_column)
    if (
        base is None
        or spec.rules.sizing.volatility_target is None
        or spec.rules.sizing.volatility_column is None
    ):
        return base
    observed = _optional_float_from_row(row, spec.rules.sizing.volatility_column)
    if observed is None or observed <= 0:
        return base
    scaled = base * spec.rules.sizing.volatility_target / observed
    cap = spec.rules.sizing.max_volatility_scaled_position_weight
    return min(scaled, cap) if cap is not None else scaled


def _signal_notional_usd(row: dict[str, Any], spec: StrategyAuthoringSpec) -> float | None:
    regime = _matching_regime_override(row, spec)
    fixed = _regime_value(regime, "notional_usd", spec.rules.sizing.notional_usd)
    return _sizing_value(row, fixed=fixed, column=spec.rules.sizing.notional_usd_column)


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


def _format_condition(condition: Condition) -> str:
    target = (
        f"column:{condition.value_column}"
        if condition.value_column is not None
        else condition.value
        if condition.value is not None
        else ""
    )
    return f"{condition.column} {condition.op} {target}".rstrip()


def _side_from_column(row: dict[str, Any], column: str) -> Literal["long", "short", "none"]:
    value = str(row.get(column) or "").strip().lower()
    if value in {"buy", "bull", "long"}:
        return "long"
    if value in {"sell", "bear", "short"}:
        return "short"
    if value in {"", "hold", "none", "skip", "flat"}:
        return "none"
    raise StrategyAuthoringValidationError(f"Unsupported side value in {column}: {value}")


def _selected_side(
    row: dict[str, Any], rules: AuthoringRules
) -> tuple[Literal["long", "short", "none"] | None, str | None]:
    long_pass = _entry_passes(row, rules.long_entry) if rules.long_entry is not None else False
    short_pass = _entry_passes(row, rules.short_entry) if rules.short_entry is not None else False
    if long_pass and short_pass:
        return "none", "ambiguous_side"
    if long_pass:
        return "long", None
    if short_pass:
        return "short", None
    if rules.side_column is not None:
        if not _entry_passes(row, rules.entry):
            return None, None
        side = _side_from_column(row, rules.side_column)
        return (side, None) if side != "none" else ("none", "side_column_hold")
    if _entry_passes(row, rules.entry):
        if rules.side == "auto":
            if rules.cross_sectional.enabled:
                return "long", None
            return None, None
        return rules.side, None
    return None, None


def _compiled_signal_id(spec: StrategyAuthoringSpec, row: dict[str, Any], *, side: str) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts_signal"),
            "execution_symbol": row.get("execution_symbol"),
            "side": side,
            "reason_code": spec.rules.reason_code,
        }
    )


def _block_trade_row(
    row: dict[str, Any],
    *,
    spec: StrategyAuthoringSpec,
    block_reason: str,
) -> dict[str, Any]:
    blocked = dict(row)
    blocked["side"] = "none"
    blocked["signal_id"] = _compiled_signal_id(spec, blocked, side="none")
    blocked["confidence"] = 0.0
    blocked["stop_loss_bps"] = None
    blocked["take_profit_bps"] = None
    blocked["min_reward_risk_ratio"] = row.get("min_reward_risk_ratio")
    blocked["reward_risk_ratio"] = row.get("reward_risk_ratio")
    blocked["trailing_stop_bps"] = None
    blocked["trailing_stop_activation_bps"] = None
    blocked["partial_take_profit_bps"] = None
    blocked["partial_exit_fraction"] = None
    blocked["min_holding_minutes"] = None
    blocked["max_holding_minutes"] = None
    blocked["exit_priority"] = DEFAULT_EXIT_PRIORITY
    blocked["exit_on_opposite_signal"] = False
    blocked["bracket_type"] = "none"
    blocked["bracket_time_stop_minutes"] = None
    blocked["bracket_break_even_after_bps"] = None
    blocked["bracket_break_even_after_partial_take_profit"] = False
    blocked["entry_order_type"] = "market"
    blocked["entry_limit_offset_bps"] = None
    blocked["entry_stop_offset_bps"] = None
    blocked["entry_timeout_minutes"] = None
    blocked["entry_time_in_force"] = "gtc"
    blocked["entry_post_only"] = False
    blocked["entry_reduce_only"] = False
    blocked["slippage_bps"] = 0.0
    blocked["max_fill_fraction"] = 0.0
    blocked["min_fill_fraction"] = None
    blocked["max_spread_bps"] = None
    blocked["min_depth_usd"] = None
    blocked["depth_column"] = None
    blocked["depth_participation_rate"] = 0.0
    blocked["max_latency_ms"] = None
    blocked["latency_ms"] = None
    blocked["min_queue_position_score"] = None
    blocked["queue_position_score"] = None
    blocked["min_borrow_availability_ratio"] = None
    blocked["borrow_availability_ratio"] = None
    blocked["max_borrow_cost_bps"] = None
    blocked["borrow_cost_bps"] = None
    blocked["position_weight"] = 0.0
    blocked["notional_usd"] = None
    blocked["_cross_sectional_group"] = row.get("_cross_sectional_group")
    blocked["_portfolio_group"] = row.get("_portfolio_group")
    blocked["_portfolio_turnover_weight"] = row.get("_portfolio_turnover_weight")
    blocked["reason_codes"] = [spec.rules.hold_reason_code]
    blocked["block_reasons"] = [*list(row.get("block_reasons") or []), block_reason]
    return blocked


def _reward_risk_ratio(row: dict[str, Any]) -> float | None:
    stop_loss_bps = row.get("stop_loss_bps")
    take_profit_bps = row.get("take_profit_bps")
    if stop_loss_bps is None or take_profit_bps is None:
        return None
    stop = float(stop_loss_bps)
    if stop <= 0:
        return None
    return float(take_profit_bps) / stop


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


def _score_value(row: dict[str, Any]) -> float | None:
    value = row.get("raw_score")
    return float(value) if isinstance(value, int | float) else None


def _signal_timestamp(row: dict[str, Any]) -> datetime:
    value = row["ts_signal"]
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise StrategyAuthoringValidationError(f"Unsupported ts_signal value: {value!r}")


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


def _apply_position_state_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    position = spec.rules.position
    if (
        not position.enabled
        and not spec.rules.order.reduce_only
        and spec.rules.order.reduce_only_column is None
    ):
        return rows

    horizon_minutes = position.holding_horizon_minutes or spec.backtest.label_horizon_minutes
    active_by_symbol: dict[str, list[tuple[datetime, str, float]]] = {}
    selected: list[dict[str, Any]] = []

    def compact_active(
        active: list[tuple[datetime, str, float]], weight: float
    ) -> list[tuple[datetime, str, float]]:
        if weight <= 0:
            return []
        end_at = max(
            (item_end_at for item_end_at, _item_side, _item_weight in active), default=None
        )
        if end_at is None:
            return []
        sides = [item_side for _item_end_at, item_side, item_weight in active if item_weight > 0]
        side = sides[0] if sides else "long"
        return [(end_at, side, weight)]

    def reduce_active_side(
        active: list[tuple[datetime, str, float]], side: str, fraction: float
    ) -> list[tuple[datetime, str, float]]:
        total = sum(weight for _end_at, active_side, weight in active if active_side == side)
        to_reduce = total * min(max(fraction, 0.0), 1.0)
        updated: list[tuple[datetime, str, float]] = []
        for end_at, active_side, weight in active:
            if active_side != side or to_reduce <= 0:
                updated.append((end_at, active_side, weight))
                continue
            reduced = min(weight, to_reduce)
            remaining = weight - reduced
            to_reduce -= reduced
            if remaining > 0:
                updated.append((end_at, active_side, remaining))
        return updated

    for row in sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"])):
        if row.get("side") == "none":
            selected.append(row)
            continue

        ts_signal = _signal_timestamp(row)
        symbol = str(row["execution_symbol"])
        active = [
            (end_at, active_side, weight)
            for end_at, active_side, weight in active_by_symbol.get(symbol, [])
            if end_at > ts_signal
        ]
        active_by_symbol[symbol] = active
        open_weight = sum(weight for _end_at, _active_side, weight in active)
        side = str(row.get("side") or "")

        if side in {"close", "reduce", "add", "rebalance"}:
            if position.require_open_position_for_markers and open_weight <= 0:
                selected.append(
                    _block_trade_row(row, spec=spec, block_reason="position_marker_without_open")
                )
                continue
            if side == "close":
                active_by_symbol[symbol] = []
            elif side == "reduce" and open_weight > 0:
                reduce_fraction = row.get("reduce_fraction")
                fraction = (
                    min(max(float(reduce_fraction), 0.0), 1.0)
                    if isinstance(reduce_fraction, int | float)
                    else 1.0
                )
                active_by_symbol[symbol] = compact_active(active, open_weight * (1.0 - fraction))
            elif side == "add" and open_weight > 0:
                add_fraction = row.get("add_fraction")
                added_weight = (
                    max(float(add_fraction), 0.0) if isinstance(add_fraction, int | float) else 1.0
                )
                if (
                    position.max_open_position_weight_per_symbol is not None
                    and open_weight + added_weight > position.max_open_position_weight_per_symbol
                ):
                    selected.append(
                        _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
                    )
                    continue
                active_by_symbol[symbol] = compact_active(active, open_weight + added_weight)
            elif side == "rebalance" and open_weight > 0:
                target_fraction = row.get("rebalance_target_fraction")
                target_weight = (
                    max(float(target_fraction), 0.0)
                    if isinstance(target_fraction, int | float)
                    else open_weight
                )
                if (
                    position.max_open_position_weight_per_symbol is not None
                    and target_weight > position.max_open_position_weight_per_symbol
                ):
                    selected.append(
                        _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
                    )
                    continue
                active_by_symbol[symbol] = compact_active(active, target_weight)
            selected.append(row)
            continue

        weight = abs(_position_weight_value(row))
        if row.get("entry_reduce_only") and side in {"long", "short"}:
            opposing_side = "short" if side == "long" else "long"
            opposing_weight = sum(
                active_weight
                for _end_at, active_side, active_weight in active
                if active_side == opposing_side
            )
            if opposing_weight <= 0:
                selected.append(
                    _block_trade_row(
                        row, spec=spec, block_reason="position_reduce_only_without_opposing_open"
                    )
                )
                continue
            reduce_fraction = row.get("reduce_fraction")
            fraction = (
                min(max(float(reduce_fraction), 0.0), 1.0)
                if isinstance(reduce_fraction, int | float)
                else 1.0
            )
            active_by_symbol[symbol] = reduce_active_side(active, opposing_side, fraction)
            reduce_row = dict(row)
            reduce_row["side"] = "reduce"
            reduce_row["signal_id"] = _compiled_signal_id(spec, reduce_row, side="reduce")
            reduce_row["position_weight"] = 0.0
            reduce_row["notional_usd"] = None
            reduce_row["reason_codes"] = [*list(row.get("reason_codes") or []), "reduce_only"]
            selected.append(reduce_row)
            continue
        if not position.allow_opposing_open_positions and side in {"long", "short"}:
            opposing_side = "short" if side == "long" else "long"
            opposing_weight = sum(
                active_weight
                for _end_at, active_side, active_weight in active
                if active_side == opposing_side
            )
            if opposing_weight > 0:
                selected.append(
                    _block_trade_row(row, spec=spec, block_reason="position_opposing_open_position")
                )
                continue
        if not position.allow_pyramiding and side in {"long", "short"}:
            same_side_weight = sum(
                active_weight
                for _end_at, active_side, active_weight in active
                if active_side == side
            )
            if same_side_weight > 0:
                selected.append(
                    _block_trade_row(row, spec=spec, block_reason="position_pyramiding_not_allowed")
                )
                continue

        if (
            position.max_open_signals_per_symbol is not None
            and len(active) >= position.max_open_signals_per_symbol
        ):
            selected.append(
                _block_trade_row(row, spec=spec, block_reason="position_open_signal_limit")
            )
            continue
        if (
            position.max_open_position_weight_per_symbol is not None
            and open_weight + weight > position.max_open_position_weight_per_symbol
        ):
            selected.append(
                _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
            )
            continue

        active.append((ts_signal + timedelta(minutes=horizon_minutes), side, weight))
        active_by_symbol[symbol] = active
        selected.append(row)
    return selected


def _apply_portfolio_allocation(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.allocation_method == "none":
        return rows

    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        target = _portfolio_target_total_position_weight(timestamp_rows, portfolio)
        if target is None:
            selected.extend(timestamp_rows)
            continue
        if portfolio.allocation_method in {
            "dollar_neutral",
            "beta_neutral",
            "group_neutral",
        }:
            selected.extend(
                _neutral_allocated_rows(
                    timestamp_rows,
                    target=target,
                    method=portfolio.allocation_method,
                )
            )
            continue
        raw_weights = _allocation_raw_weights(timestamp_rows, portfolio)
        total_raw = sum(raw_weights)
        for row, raw_weight in zip(timestamp_rows, raw_weights, strict=True):
            allocated = 0.0 if total_raw == 0.0 else target * raw_weight / total_raw
            updated = dict(row)
            updated["position_weight"] = allocated
            selected.append(updated)
    return selected


def _portfolio_target_total_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    column = portfolio.target_total_position_weight_column
    if column is None:
        return portfolio.target_total_position_weight
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.target_total_position_weight,
        value_key="_portfolio_target_total_position_weight",
        field_name="rules.portfolio.target_total_position_weight_column",
    )


def _portfolio_timestamp_limit(
    rows: list[dict[str, Any]],
    *,
    fixed: float | None,
    value_key: str,
    field_name: str,
) -> float | None:
    resolved: list[float] = []
    for row in rows:
        raw_value = row.get(value_key)
        value = float(raw_value) if isinstance(raw_value, int | float) else None
        if value is None:
            continue
        if value < 0:
            raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
        resolved.append(value)
    if not resolved:
        return fixed
    first = resolved[0]
    if any(not math.isclose(value, first, rel_tol=0.0, abs_tol=1e-12) for value in resolved[1:]):
        raise StrategyAuthoringValidationError(
            f"{field_name} must resolve to one value per timestamp"
        )
    return first


def _allocation_raw_weights(rows: list[dict[str, Any]], portfolio: PortfolioRules) -> list[float]:
    if portfolio.allocation_method == "equal_weight":
        return [1.0 for _row in rows]
    if portfolio.allocation_method == "score_proportional":
        raw_weights = [
            max(0.0, float(row["raw_score"]))
            if isinstance(row.get("raw_score"), int | float)
            else 0.0
            for row in rows
        ]
        return (
            raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]
        )
    raw_weights = [
        1.0 / float(row["_allocation_volatility"])
        if isinstance(row.get("_allocation_volatility"), int | float)
        and float(row["_allocation_volatility"]) > 0.0
        else 0.0
        for row in rows
    ]
    return raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]


def _neutral_allocated_rows(
    rows: list[dict[str, Any]], *, target: float, method: str
) -> list[dict[str, Any]]:
    if method == "group_neutral":
        group_rows: dict[str, list[dict[str, Any]]] = {}
        ungrouped: list[dict[str, Any]] = []
        for row in rows:
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_rows.setdefault(group, []).append(row)
            else:
                ungrouped.append(row)
        group_target = target / len(group_rows) if group_rows else 0.0
        allocated: list[dict[str, Any]] = []
        for grouped_rows in group_rows.values():
            allocated.extend(
                _side_neutral_allocated_rows(
                    grouped_rows,
                    long_target=group_target / 2.0,
                    short_target=group_target / 2.0,
                )
            )
        allocated.extend(_side_neutral_allocated_rows(ungrouped, long_target=0.0, short_target=0.0))
        return allocated

    long_target = target / 2.0
    short_target = target / 2.0
    if method == "beta_neutral":
        long_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "long")
        short_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "short")
        if long_beta > 0.0 and short_beta > 0.0:
            long_target = target * short_beta / (long_beta + short_beta)
            short_target = target * long_beta / (long_beta + short_beta)
    return _side_neutral_allocated_rows(rows, long_target=long_target, short_target=short_target)


def _weighted_average_abs_beta(rows: Iterable[dict[str, Any]]) -> float:
    weighted_beta = 0.0
    total_weight = 0.0
    for row in rows:
        beta = row.get("_allocation_beta")
        if not isinstance(beta, int | float):
            continue
        weight = abs(_position_weight_value(row))
        weighted_beta += abs(float(beta)) * weight
        total_weight += weight
    return 0.0 if total_weight == 0.0 else weighted_beta / total_weight


def _side_neutral_allocated_rows(
    rows: list[dict[str, Any]], *, long_target: float, short_target: float
) -> list[dict[str, Any]]:
    by_side = {
        "long": [row for row in rows if row.get("side") == "long"],
        "short": [row for row in rows if row.get("side") == "short"],
    }
    allocated: list[dict[str, Any]] = []
    for side, side_rows in by_side.items():
        side_target = long_target if side == "long" else short_target
        total_raw = sum(abs(_position_weight_value(row)) for row in side_rows)
        for row in side_rows:
            updated = dict(row)
            updated["position_weight"] = (
                0.0
                if total_raw == 0.0
                else side_target * abs(_position_weight_value(row)) / total_raw
            )
            allocated.append(updated)
    return allocated


def _position_weight_value(row: dict[str, Any]) -> float:
    value = row.get("position_weight")
    return float(value) if isinstance(value, int | float) else 1.0


def _portfolio_turnover_weight_value(row: dict[str, Any]) -> float:
    value = row.get("_portfolio_turnover_weight")
    if isinstance(value, int | float):
        return abs(float(value))
    return abs(_position_weight_value(row))


def _apply_portfolio_turnover_budget(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.max_turnover_weight_per_timestamp is None:
        return rows

    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        used_turnover = 0.0
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            turnover_weight = _portfolio_turnover_weight_value(row)
            if used_turnover + turnover_weight > portfolio.max_turnover_weight_per_timestamp:
                blocked_rows.append(
                    _block_trade_row(row, spec=spec, block_reason="portfolio_turnover_budget_limit")
                )
                continue
            used_turnover += turnover_weight
            accepted_rows.append(row)
        selected.extend([*blocked_rows, *accepted_rows])
    return selected


def _portfolio_exposure_block_reason(
    row: dict[str, Any],
    *,
    portfolio: PortfolioRules,
    max_total_position_weight: float | None,
    max_long_position_weight: float | None,
    max_short_position_weight: float | None,
    max_symbol_position_weight: float | None,
    max_group_position_weight: float | None,
    total_weight: float,
    long_weight: float,
    short_weight: float,
    symbol_weights: dict[str, float],
    group_weights: dict[str, float],
) -> str | None:
    weight = abs(_position_weight_value(row))
    side = str(row.get("side") or "")
    symbol = str(row.get("execution_symbol") or "")
    group = str(row.get("_portfolio_group") or "").strip()
    if max_total_position_weight is not None and total_weight + weight > max_total_position_weight:
        return "portfolio_total_exposure_limit"
    if side == "long" and max_long_position_weight is not None:
        if long_weight + weight > max_long_position_weight:
            return "portfolio_long_exposure_limit"
    if side == "short" and max_short_position_weight is not None:
        if short_weight + weight > max_short_position_weight:
            return "portfolio_short_exposure_limit"
    if max_symbol_position_weight is not None:
        if symbol_weights.get(symbol, 0.0) + weight > max_symbol_position_weight:
            return "portfolio_symbol_exposure_limit"
    if (
        max_group_position_weight is not None
        or portfolio.max_group_abs_net_position_weight is not None
        or portfolio.max_group_abs_net_position_weight_column is not None
    ):
        if not group:
            return "portfolio_group_missing"
    if max_group_position_weight is not None:
        if group_weights.get(group, 0.0) + weight > max_group_position_weight:
            return "portfolio_group_exposure_limit"
    return None


def _portfolio_max_long_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_long_position_weight,
        value_key="_portfolio_max_long_position_weight",
        field_name="rules.portfolio.max_long_position_weight_column",
    )


def _portfolio_max_short_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_short_position_weight,
        value_key="_portfolio_max_short_position_weight",
        field_name="rules.portfolio.max_short_position_weight_column",
    )


def _portfolio_max_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_abs_net_position_weight,
        value_key="_portfolio_max_abs_net_position_weight",
        field_name="rules.portfolio.max_abs_net_position_weight_column",
    )


def _portfolio_max_symbol_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_symbol_position_weight,
        value_key="_portfolio_max_symbol_position_weight",
        field_name="rules.portfolio.max_symbol_position_weight_column",
    )


def _portfolio_max_group_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_group_position_weight,
        value_key="_portfolio_max_group_position_weight",
        field_name="rules.portfolio.max_group_position_weight_column",
    )


def _portfolio_max_group_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_group_abs_net_position_weight,
        value_key="_portfolio_max_group_abs_net_position_weight",
        field_name="rules.portfolio.max_group_abs_net_position_weight_column",
    )


def _apply_portfolio_exposure_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if not portfolio.exposure_limits_enabled:
        return rows
    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        max_total_position_weight = _portfolio_timestamp_limit(
            timestamp_rows,
            fixed=portfolio.max_total_position_weight,
            value_key="_portfolio_max_total_position_weight",
            field_name="rules.portfolio.max_total_position_weight_column",
        )
        max_long_position_weight = _portfolio_max_long_position_weight(timestamp_rows, portfolio)
        max_short_position_weight = _portfolio_max_short_position_weight(timestamp_rows, portfolio)
        max_symbol_position_weight = _portfolio_max_symbol_position_weight(
            timestamp_rows, portfolio
        )
        max_group_position_weight = _portfolio_max_group_position_weight(timestamp_rows, portfolio)
        max_abs_net_position_weight = _portfolio_max_abs_net_position_weight(
            timestamp_rows, portfolio
        )
        max_group_abs_net_position_weight = _portfolio_max_group_abs_net_position_weight(
            timestamp_rows, portfolio
        )
        total_weight = 0.0
        long_weight = 0.0
        short_weight = 0.0
        symbol_weights: dict[str, float] = {}
        group_weights: dict[str, float] = {}
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            reason = _portfolio_exposure_block_reason(
                row,
                portfolio=portfolio,
                max_total_position_weight=max_total_position_weight,
                max_long_position_weight=max_long_position_weight,
                max_short_position_weight=max_short_position_weight,
                max_symbol_position_weight=max_symbol_position_weight,
                max_group_position_weight=max_group_position_weight,
                total_weight=total_weight,
                long_weight=long_weight,
                short_weight=short_weight,
                symbol_weights=symbol_weights,
                group_weights=group_weights,
            )
            if reason is not None:
                blocked_rows.append(_block_trade_row(row, spec=spec, block_reason=reason))
                continue
            weight = abs(_position_weight_value(row))
            total_weight += weight
            if row.get("side") == "long":
                long_weight += weight
            elif row.get("side") == "short":
                short_weight += weight
            symbol = str(row.get("execution_symbol") or "")
            symbol_weights[symbol] = symbol_weights.get(symbol, 0.0) + weight
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_weights[group] = group_weights.get(group, 0.0) + weight
            accepted_rows.append(row)
        accepted_rows, net_blocked_rows = _apply_portfolio_net_exposure_limit(
            accepted_rows,
            max_abs_net_position_weight=max_abs_net_position_weight,
            spec=spec,
        )
        accepted_rows, group_net_blocked_rows = _apply_portfolio_group_net_exposure_limit(
            accepted_rows,
            max_group_abs_net_position_weight=max_group_abs_net_position_weight,
            spec=spec,
        )
        selected.extend([*blocked_rows, *net_blocked_rows, *group_net_blocked_rows, *accepted_rows])
    return selected


def _apply_portfolio_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        long_weight = sum(
            abs(_position_weight_value(row)) for row in accepted if row.get("side") == "long"
        )
        short_weight = sum(
            abs(_position_weight_value(row)) for row in accepted if row.get("side") == "short"
        )
        net_weight = long_weight - short_weight
        if abs(net_weight) <= max_abs_net_position_weight:
            return accepted, blocked

        overweight_side = "long" if net_weight > 0 else "short"
        candidates = [
            (index, row) for index, row in enumerate(accepted) if row.get("side") == overweight_side
        ]
        if not candidates:
            return accepted, blocked

        remove_index, row = min(
            candidates,
            key=lambda item: (
                item[1].get("rank_score") if item[1].get("rank_score") is not None else -1.0,
                item[0],
            ),
        )
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_net_exposure_limit")
        )
        accepted.pop(remove_index)


def _apply_portfolio_group_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_group_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_group_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        group_rows: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for index, row in enumerate(accepted):
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_rows.setdefault(group, []).append((index, row))

        over_limit: tuple[str, float] | None = None
        for group, indexed_rows in group_rows.items():
            long_weight = sum(
                abs(_position_weight_value(row))
                for _index, row in indexed_rows
                if row.get("side") == "long"
            )
            short_weight = sum(
                abs(_position_weight_value(row))
                for _index, row in indexed_rows
                if row.get("side") == "short"
            )
            net_weight = long_weight - short_weight
            if abs(net_weight) > max_group_abs_net_position_weight:
                over_limit = (group, net_weight)
                break
        if over_limit is None:
            return accepted, blocked

        group, net_weight = over_limit
        overweight_side = "long" if net_weight > 0 else "short"
        candidates = [
            (index, row)
            for index, row in enumerate(accepted)
            if row.get("side") == overweight_side
            and str(row.get("_portfolio_group") or "").strip() == group
        ]
        if not candidates:
            return accepted, blocked

        remove_index, row = min(
            candidates,
            key=lambda item: (
                item[1].get("rank_score") if item[1].get("rank_score") is not None else -1.0,
                item[0],
            ),
        )
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_group_net_exposure_limit")
        )
        accepted.pop(remove_index)


def _apply_cross_sectional_selection(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if not spec.rules.cross_sectional.enabled:
        return rows
    passthrough = [row for row in rows if row.get("side") == "none"]
    candidates_by_timestamp: dict[tuple[Any, str | None], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("side") == "none":
            continue
        group: str | None = None
        if spec.rules.cross_sectional.group_column is not None:
            group = str(row.get("_cross_sectional_group") or "").strip()
            if not group:
                passthrough.append(
                    _block_trade_row(
                        row,
                        spec=spec,
                        block_reason="cross_sectional_group_missing",
                    )
                )
                continue
        candidates_by_timestamp.setdefault((row["ts_signal"], group), []).append(row)

    selected_rows: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in candidates_by_timestamp.values():
        scored = [row for row in timestamp_rows if _score_value(row) is not None]
        unscored = [row for row in timestamp_rows if _score_value(row) is None]
        if (
            spec.rules.cross_sectional.min_candidates is not None
            and len(scored) < spec.rules.cross_sectional.min_candidates
        ):
            selected_rows.extend(
                _block_trade_row(row, spec=spec, block_reason="cross_sectional_min_candidates")
                for row in timestamp_rows
            )
            continue
        sorted_desc = sorted(scored, key=lambda item: _score_value(item) or 0.0, reverse=True)
        sorted_asc = list(reversed(sorted_desc))
        percentile_by_id: dict[str, float] = {}
        denominator = max(len(sorted_desc) - 1, 1)
        for index, row in enumerate(sorted_desc):
            percentile_by_id[str(row["signal_id"])] = (
                1.0 if len(sorted_desc) == 1 else 1.0 - (index / denominator)
            )

        top_n = _cross_sectional_selection_count(
            len(scored),
            fixed_count=spec.rules.cross_sectional.long_top_n,
            fraction=spec.rules.cross_sectional.long_top_fraction,
        )
        bottom_n = _cross_sectional_selection_count(
            len(scored),
            fixed_count=spec.rules.cross_sectional.short_bottom_n,
            fraction=spec.rules.cross_sectional.short_bottom_fraction,
        )
        unscored_ids = {str(row["signal_id"]) for row in unscored}
        top_ids = {str(row["signal_id"]) for row in sorted_desc[:top_n]}
        bottom_ids = {
            str(row["signal_id"])
            for row in sorted_asc[:bottom_n]
            if str(row["signal_id"]) not in top_ids
        }
        for row in timestamp_rows:
            row_id = str(row["signal_id"])
            if row_id in unscored_ids:
                selected_rows.append(
                    _block_trade_row(
                        row,
                        spec=spec,
                        block_reason="cross_sectional_score_missing",
                    )
                )
                continue
            updated = dict(row)
            percentile = percentile_by_id[row_id]
            updated["rank_score"] = percentile
            updated["percentile_rank"] = percentile
            updated["tail_bucket"] = _tail_bucket(percentile)
            if row_id in top_ids:
                if (
                    spec.rules.cross_sectional.min_long_score is not None
                    and (_score_value(row) or 0.0) < spec.rules.cross_sectional.min_long_score
                ):
                    selected_rows.append(
                        _block_trade_row(
                            updated,
                            spec=spec,
                            block_reason="cross_sectional_long_score_threshold",
                        )
                    )
                    continue
                updated["side"] = "long"
                updated["signal_id"] = _compiled_signal_id(spec, updated, side="long")
                updated["reason_codes"] = [
                    *list(row.get("reason_codes") or []),
                    "cross_sectional_top",
                ]
                selected_rows.append(updated)
            elif row_id in bottom_ids:
                if (
                    spec.rules.cross_sectional.max_short_score is not None
                    and (_score_value(row) or 0.0) > spec.rules.cross_sectional.max_short_score
                ):
                    selected_rows.append(
                        _block_trade_row(
                            updated,
                            spec=spec,
                            block_reason="cross_sectional_short_score_threshold",
                        )
                    )
                    continue
                updated["side"] = "short"
                updated["signal_id"] = _compiled_signal_id(spec, updated, side="short")
                updated["reason_codes"] = [
                    *list(row.get("reason_codes") or []),
                    "cross_sectional_bottom",
                ]
                selected_rows.append(updated)
            else:
                selected_rows.append(
                    _block_trade_row(
                        updated,
                        spec=spec,
                        block_reason="cross_sectional_rank_filter",
                    )
                )
    return selected_rows


def _cross_sectional_selection_count(
    candidate_count: int, *, fixed_count: int | None, fraction: float | None
) -> int:
    if fixed_count is not None:
        return fixed_count
    if fraction is None or candidate_count <= 0:
        return 0
    return max(1, math.ceil(candidate_count * fraction))


def _signal_id(
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    *,
    side: str | None = None,
) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts"),
            "execution_symbol": binding.execution_symbol,
            "side": side or spec.rules.side,
            "reason_code": spec.rules.reason_code,
        }
    )


def _multi_leg_group_id(
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    *,
    base_side: str,
) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts"),
            "canonical_symbol": row.get("canonical_symbol"),
            "anchor_real_market_symbol": spec.rules.multi_leg.anchor_real_market_symbol,
            "base_side": base_side,
            "reason_code": spec.rules.reason_code,
        }
    )


def _resolve_leg_side(base_side: str, leg_side: str) -> Literal["long", "short"]:
    if leg_side == "long":
        return "long"
    if leg_side == "short":
        return "short"
    if leg_side == "same":
        return "short" if base_side == "short" else "long"
    return "long" if base_side == "short" else "short"


def _close_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="close"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "close",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
        "min_reward_risk_ratio": None,
        "reward_risk_ratio": None,
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "max_holding_minutes": None,
        "exit_priority": DEFAULT_EXIT_PRIORITY,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "exit_on_add_signal": False,
        "add_fraction": None,
        "exit_on_rebalance_signal": False,
        "rebalance_target_fraction": None,
        "rebalance_min_delta_fraction": None,
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "bracket_break_even_after_partial_take_profit": False,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "entry_reduce_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "correlation_crowding_score": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.close_reason_code],
        "block_reasons": [],
    }


def _reduce_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="reduce"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "reduce",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
        "min_reward_risk_ratio": None,
        "reward_risk_ratio": None,
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "max_holding_minutes": None,
        "exit_priority": DEFAULT_EXIT_PRIORITY,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.reduce_fraction,
            column=spec.rules.exit.reduce_fraction_column,
        ),
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "bracket_break_even_after_partial_take_profit": False,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "entry_reduce_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "correlation_crowding_score": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.reduce_reason_code],
        "block_reasons": [],
    }


def _add_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="add"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "add",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
        "min_reward_risk_ratio": None,
        "reward_risk_ratio": None,
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "max_holding_minutes": None,
        "exit_priority": DEFAULT_EXIT_PRIORITY,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "exit_on_add_signal": False,
        "add_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.add_fraction,
            column=spec.rules.exit.add_fraction_column,
        ),
        "exit_on_rebalance_signal": False,
        "rebalance_target_fraction": None,
        "rebalance_min_delta_fraction": None,
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "bracket_break_even_after_partial_take_profit": False,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "entry_reduce_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "correlation_crowding_score": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.add_reason_code],
        "block_reasons": [],
    }


def _rebalance_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="rebalance"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "rebalance",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
        "min_reward_risk_ratio": None,
        "reward_risk_ratio": None,
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "max_holding_minutes": None,
        "exit_priority": DEFAULT_EXIT_PRIORITY,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "exit_on_add_signal": False,
        "add_fraction": None,
        "exit_on_rebalance_signal": False,
        "rebalance_target_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.rebalance_target_fraction,
            column=spec.rules.exit.rebalance_target_fraction_column,
        ),
        "rebalance_min_delta_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.rebalance_min_delta_fraction,
            column=spec.rules.exit.rebalance_min_delta_fraction_column,
        ),
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "bracket_break_even_after_partial_take_profit": False,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "entry_reduce_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "correlation_crowding_score": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.rebalance_reason_code],
        "block_reasons": [],
    }


def _trade_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
    position_weight: float | None = None,
    notional_usd: float | None = None,
    exit_overrides: dict[str, float | None] | None = None,
    order_overrides: dict[str, Any] | None = None,
    execution_overrides: dict[str, Any] | None = None,
    multi_leg_group_id: str | None = None,
    multi_leg_leg_index: int | None = None,
    multi_leg_leg_count: int | None = None,
    multi_leg_anchor_real_market_symbol: str | None = None,
    reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    regime = _matching_regime_override(row, spec)
    effective_reason_codes = reason_codes or [spec.rules.reason_code]
    if regime is not None:
        effective_reason_codes = [*effective_reason_codes, f"regime:{regime.name}"]
    reduce_only = (
        _optional_bool_from_row(
            row,
            _override_column(order_overrides, "reduce_only", spec.rules.order.reduce_only_column),
        )
        if _override_column(order_overrides, "reduce_only", spec.rules.order.reduce_only_column)
        is not None
        else None
    )
    reduce_only = (
        _override_value(order_overrides, "reduce_only", spec.rules.order.reduce_only)
        if reduce_only is None
        else reduce_only
    )
    entry_timeout_minutes = _minutes_value(
        row,
        fixed=_override_value(order_overrides, "timeout_minutes", spec.rules.order.timeout_minutes),
        column=_override_column(
            order_overrides, "timeout_minutes", spec.rules.order.timeout_minutes_column
        ),
    )
    entry_time_in_force = _time_in_force_value(
        row,
        fixed=_override_value(order_overrides, "time_in_force", spec.rules.order.time_in_force),
        column=_override_column(
            order_overrides, "time_in_force", spec.rules.order.time_in_force_column
        ),
    )
    if entry_time_in_force == "gtd" and entry_timeout_minutes is None:
        raise StrategyAuthoringValidationError(
            "rules.order.timeout_minutes or timeout_minutes_column is required "
            "when row time_in_force is gtd"
        )
    if entry_time_in_force in {"ioc", "fok"} and entry_timeout_minutes is not None:
        raise StrategyAuthoringValidationError(
            "rules.order.timeout_minutes cannot be set when row time_in_force is ioc or fok"
        )
    entry_order_type = _entry_type_value(
        row,
        fixed=_override_value(order_overrides, "entry_type", spec.rules.order.entry_type),
        column=_override_column(order_overrides, "entry_type", spec.rules.order.entry_type_column),
    )
    entry_limit_offset_bps = _non_negative_bps_value(
        row,
        fixed=_override_value(
            order_overrides, "limit_offset_bps", spec.rules.order.limit_offset_bps
        ),
        column=_override_column(
            order_overrides, "limit_offset_bps", spec.rules.order.limit_offset_bps_column
        ),
        field_name="rules.order.limit_offset_bps",
    )
    entry_stop_offset_bps = _non_negative_bps_value(
        row,
        fixed=_override_value(order_overrides, "stop_offset_bps", spec.rules.order.stop_offset_bps),
        column=_override_column(
            order_overrides, "stop_offset_bps", spec.rules.order.stop_offset_bps_column
        ),
        field_name="rules.order.stop_offset_bps",
    )
    if entry_order_type == "limit" and entry_limit_offset_bps is None:
        raise StrategyAuthoringValidationError(
            "rules.order.limit_offset_bps or limit_offset_bps_column is required "
            "when row entry_type is limit"
        )
    if entry_order_type == "stop_market" and entry_stop_offset_bps is None:
        raise StrategyAuthoringValidationError(
            "rules.order.stop_offset_bps or stop_offset_bps_column is required "
            "when row entry_type is stop_market"
        )
    post_only = (
        _optional_bool_from_row(
            row,
            _override_column(order_overrides, "post_only", spec.rules.order.post_only_column),
        )
        if _override_column(order_overrides, "post_only", spec.rules.order.post_only_column)
        is not None
        else None
    )
    post_only = (
        _override_value(order_overrides, "post_only", spec.rules.order.post_only)
        if post_only is None
        else post_only
    )
    if post_only and entry_order_type != "limit":
        raise StrategyAuthoringValidationError(
            "rules.order.post_only is only supported for limit entry"
        )
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side=side),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "multi_leg_group_id": multi_leg_group_id,
        "multi_leg_leg_index": multi_leg_leg_index,
        "multi_leg_leg_count": multi_leg_leg_count,
        "multi_leg_anchor_real_market_symbol": multi_leg_anchor_real_market_symbol,
        "side": side,
        "raw_score": raw_score,
        "rank_score": rank,
        "percentile_rank": rank,
        "tail_bucket": _tail_bucket(rank),
        "confidence": spec.rules.confidence,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "stop_loss_bps",
                _regime_value(regime, "stop_loss_bps", spec.rules.exit.stop_loss_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "stop_loss_bps", spec.rules.exit.stop_loss_bps_column
            ),
        ),
        "min_stop_loss_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "min_stop_loss_bps",
                _regime_value(regime, "min_stop_loss_bps", spec.rules.exit.min_stop_loss_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "min_stop_loss_bps", spec.rules.exit.min_stop_loss_bps_column
            ),
        ),
        "max_stop_loss_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "max_stop_loss_bps",
                _regime_value(regime, "max_stop_loss_bps", spec.rules.exit.max_stop_loss_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "max_stop_loss_bps", spec.rules.exit.max_stop_loss_bps_column
            ),
        ),
        "take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "take_profit_bps",
                _regime_value(regime, "take_profit_bps", spec.rules.exit.take_profit_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "take_profit_bps", spec.rules.exit.take_profit_bps_column
            ),
        ),
        "min_take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "min_take_profit_bps",
                _regime_value(
                    regime,
                    "min_take_profit_bps",
                    spec.rules.exit.min_take_profit_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides, "min_take_profit_bps", spec.rules.exit.min_take_profit_bps_column
            ),
        ),
        "max_take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "max_take_profit_bps",
                _regime_value(
                    regime,
                    "max_take_profit_bps",
                    spec.rules.exit.max_take_profit_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides, "max_take_profit_bps", spec.rules.exit.max_take_profit_bps_column
            ),
        ),
        "min_reward_risk_ratio": _sizing_value(
            row,
            fixed=_exit_override(
                exit_overrides,
                "min_reward_risk_ratio",
                _regime_value(
                    regime,
                    "min_reward_risk_ratio",
                    spec.rules.exit.min_reward_risk_ratio,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "min_reward_risk_ratio",
                spec.rules.exit.min_reward_risk_ratio_column,
            ),
        ),
        "reward_risk_ratio": None,
        "trailing_stop_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "trailing_stop_bps",
                _regime_value(regime, "trailing_stop_bps", spec.rules.exit.trailing_stop_bps),
            ),
            column=_exit_override_column(
                exit_overrides, "trailing_stop_bps", spec.rules.exit.trailing_stop_bps_column
            ),
        ),
        "trailing_stop_activation_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "trailing_stop_activation_bps",
                _regime_value(
                    regime,
                    "trailing_stop_activation_bps",
                    spec.rules.exit.trailing_stop_activation_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "trailing_stop_activation_bps",
                spec.rules.exit.trailing_stop_activation_bps_column,
            ),
        ),
        "partial_take_profit_bps": _exit_bps(
            row,
            fixed=_exit_override(
                exit_overrides,
                "partial_take_profit_bps",
                _regime_value(
                    regime,
                    "partial_take_profit_bps",
                    spec.rules.exit.partial_take_profit_bps,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "partial_take_profit_bps",
                spec.rules.exit.partial_take_profit_bps_column,
            ),
        ),
        "partial_exit_fraction": _sizing_value(
            row,
            fixed=_exit_override(
                exit_overrides,
                "partial_exit_fraction",
                _regime_value(
                    regime,
                    "partial_exit_fraction",
                    spec.rules.exit.partial_exit_fraction,
                ),
            ),
            column=_exit_override_column(
                exit_overrides,
                "partial_exit_fraction",
                spec.rules.exit.partial_exit_fraction_column,
            ),
        ),
        "min_holding_minutes": _minutes_value(
            row,
            fixed=spec.rules.exit.min_holding_minutes,
            column=spec.rules.exit.min_holding_minutes_column,
        ),
        "max_holding_minutes": _minutes_value(
            row,
            fixed=spec.rules.exit.max_holding_minutes,
            column=spec.rules.exit.max_holding_minutes_column,
        ),
        "exit_priority": ",".join(spec.rules.exit.exit_priority),
        "exit_on_opposite_signal": spec.rules.exit.exit_on_opposite_signal,
        "exit_on_close_signal": spec.rules.exit.exit_on_close_signal,
        "exit_on_reduce_signal": spec.rules.exit.exit_on_reduce_signal,
        "reduce_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.reduce_fraction if reduce_only else None,
            column=(spec.rules.exit.reduce_fraction_column if reduce_only else None),
        ),
        "exit_on_add_signal": spec.rules.exit.exit_on_add_signal,
        "add_fraction": None,
        "exit_on_rebalance_signal": spec.rules.exit.exit_on_rebalance_signal,
        "rebalance_target_fraction": None,
        "rebalance_min_delta_fraction": None,
        "bracket_type": spec.rules.bracket.bracket_type if spec.rules.bracket.enabled else "none",
        "bracket_time_stop_minutes": _minutes_value(
            row,
            fixed=spec.rules.bracket.time_stop_minutes if spec.rules.bracket.enabled else None,
            column=(
                spec.rules.bracket.time_stop_minutes_column if spec.rules.bracket.enabled else None
            ),
        ),
        "bracket_break_even_after_bps": _exit_bps(
            row,
            fixed=spec.rules.bracket.break_even_after_bps if spec.rules.bracket.enabled else None,
            column=(
                spec.rules.bracket.break_even_after_bps_column
                if spec.rules.bracket.enabled
                else None
            ),
        ),
        "bracket_break_even_after_partial_take_profit": (
            spec.rules.bracket.break_even_after_partial_take_profit
            if spec.rules.bracket.enabled
            else False
        ),
        "entry_order_type": entry_order_type,
        "entry_limit_offset_bps": entry_limit_offset_bps,
        "entry_stop_offset_bps": entry_stop_offset_bps,
        "entry_timeout_minutes": entry_timeout_minutes,
        "entry_time_in_force": entry_time_in_force,
        "entry_post_only": post_only,
        "entry_reduce_only": reduce_only,
        "slippage_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "slippage_bps",
                _regime_value(regime, "slippage_bps", spec.rules.execution.slippage_bps),
            ),
            column=_override_column(
                execution_overrides,
                "slippage_bps",
                spec.rules.execution.slippage_bps_column,
            ),
        )
        or 0.0,
        "max_fill_fraction": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_fill_fraction",
                _regime_value(
                    regime,
                    "max_fill_fraction",
                    spec.rules.execution.max_fill_fraction,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_fill_fraction",
                spec.rules.execution.max_fill_fraction_column,
            ),
        ),
        "min_fill_fraction": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_fill_fraction",
                _regime_value(
                    regime,
                    "min_fill_fraction",
                    spec.rules.execution.min_fill_fraction,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "min_fill_fraction",
                spec.rules.execution.min_fill_fraction_column,
            ),
        ),
        "max_spread_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_spread_bps",
                _regime_value(regime, "max_spread_bps", spec.rules.execution.max_spread_bps),
            ),
            column=_override_column(
                execution_overrides,
                "max_spread_bps",
                spec.rules.execution.max_spread_bps_column,
            ),
        ),
        "min_depth_usd": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_depth_usd",
                _regime_value(regime, "min_depth_usd", spec.rules.execution.min_depth_usd),
            ),
            column=_override_column(
                execution_overrides,
                "min_depth_usd",
                spec.rules.execution.min_depth_usd_column,
            ),
        ),
        "depth_column": _override_value(
            execution_overrides,
            "depth_column",
            spec.rules.execution.depth_column,
        ),
        "depth_participation_rate": _override_value(
            execution_overrides,
            "depth_participation_rate",
            _regime_value(
                regime,
                "depth_participation_rate",
                spec.rules.execution.depth_participation_rate,
            ),
        ),
        "max_latency_ms": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_latency_ms",
                _regime_value(regime, "max_latency_ms", spec.rules.execution.max_latency_ms),
            ),
            column=_override_column(
                execution_overrides,
                "max_latency_ms",
                spec.rules.execution.max_latency_ms_column,
            ),
        ),
        "latency_ms": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides, "latency_column", spec.rules.execution.latency_column
            ),
        ),
        "min_queue_position_score": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_queue_position_score",
                _regime_value(
                    regime,
                    "min_queue_position_score",
                    spec.rules.execution.min_queue_position_score,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "min_queue_position_score",
                spec.rules.execution.min_queue_position_score_column,
            ),
        ),
        "queue_position_score": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "queue_position_score_column",
                spec.rules.execution.queue_position_score_column,
            ),
        ),
        "min_borrow_availability_ratio": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_borrow_availability_ratio",
                _regime_value(
                    regime,
                    "min_borrow_availability_ratio",
                    spec.rules.execution.min_borrow_availability_ratio,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "min_borrow_availability_ratio",
                spec.rules.execution.min_borrow_availability_ratio_column,
            ),
        ),
        "borrow_availability_ratio": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "borrow_availability_column",
                spec.rules.execution.borrow_availability_column,
            ),
        ),
        "max_borrow_cost_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_borrow_cost_bps",
                _regime_value(
                    regime, "max_borrow_cost_bps", spec.rules.execution.max_borrow_cost_bps
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_borrow_cost_bps",
                spec.rules.execution.max_borrow_cost_bps_column,
            ),
        ),
        "borrow_cost_bps": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "borrow_cost_column",
                spec.rules.execution.borrow_cost_column,
            ),
        ),
        "max_tax_drag_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_tax_drag_bps",
                _regime_value(
                    regime,
                    "max_tax_drag_bps",
                    spec.rules.execution.max_tax_drag_bps,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_tax_drag_bps",
                spec.rules.execution.max_tax_drag_bps_column,
            ),
        ),
        "tax_drag_bps": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides, "tax_drag_column", spec.rules.execution.tax_drag_column
            ),
        ),
        "max_turnover_pressure": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_turnover_pressure",
                _regime_value(
                    regime, "max_turnover_pressure", spec.rules.execution.max_turnover_pressure
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_turnover_pressure",
                spec.rules.execution.max_turnover_pressure_column,
            ),
        ),
        "turnover_pressure": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "turnover_pressure_column",
                spec.rules.execution.turnover_pressure_column,
            ),
        ),
        "max_capacity_usage_ratio": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_capacity_usage_ratio",
                _regime_value(
                    regime,
                    "max_capacity_usage_ratio",
                    spec.rules.execution.max_capacity_usage_ratio,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_capacity_usage_ratio",
                spec.rules.execution.max_capacity_usage_ratio_column,
            ),
        ),
        "capacity_usage_ratio": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "capacity_usage_column",
                spec.rules.execution.capacity_usage_column,
            ),
        ),
        "max_correlation_crowding_score": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_correlation_crowding_score",
                _regime_value(
                    regime,
                    "max_correlation_crowding_score",
                    spec.rules.execution.max_correlation_crowding_score,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "max_correlation_crowding_score",
                spec.rules.execution.max_correlation_crowding_score_column,
            ),
        ),
        "correlation_crowding_score": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "correlation_crowding_column",
                spec.rules.execution.correlation_crowding_column,
            ),
        ),
        "min_fee_edge_bps": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_fee_edge_bps",
                _regime_value(regime, "min_fee_edge_bps", spec.rules.execution.min_fee_edge_bps),
            ),
            column=_override_column(
                execution_overrides,
                "min_fee_edge_bps",
                spec.rules.execution.min_fee_edge_bps_column,
            ),
        ),
        "fee_edge_bps": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides, "fee_edge_column", spec.rules.execution.fee_edge_column
            ),
        ),
        "position_weight": position_weight
        if position_weight is not None
        else _signal_position_weight(row, spec),
        "notional_usd": notional_usd
        if notional_usd is not None
        else _signal_notional_usd(row, spec),
        "_cross_sectional_group": row.get(spec.rules.cross_sectional.group_column)
        if spec.rules.cross_sectional.group_column is not None
        else None,
        "_allocation_volatility": row.get(spec.rules.portfolio.allocation_volatility_column)
        if spec.rules.portfolio.allocation_volatility_column is not None
        else None,
        "_allocation_beta": row.get(spec.rules.portfolio.allocation_beta_column)
        if spec.rules.portfolio.allocation_beta_column is not None
        else None,
        "_portfolio_target_total_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.target_total_position_weight_column
        )
        if spec.rules.portfolio.target_total_position_weight_column is not None
        else None,
        "_portfolio_max_total_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_total_position_weight_column
        )
        if spec.rules.portfolio.max_total_position_weight_column is not None
        else None,
        "_portfolio_max_long_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_long_position_weight_column
        )
        if spec.rules.portfolio.max_long_position_weight_column is not None
        else None,
        "_portfolio_max_short_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_short_position_weight_column
        )
        if spec.rules.portfolio.max_short_position_weight_column is not None
        else None,
        "_portfolio_max_abs_net_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_abs_net_position_weight_column
        )
        if spec.rules.portfolio.max_abs_net_position_weight_column is not None
        else None,
        "_portfolio_max_symbol_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_symbol_position_weight_column
        )
        if spec.rules.portfolio.max_symbol_position_weight_column is not None
        else None,
        "_portfolio_max_group_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_group_position_weight_column
        )
        if spec.rules.portfolio.max_group_position_weight_column is not None
        else None,
        "_portfolio_max_group_abs_net_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_group_abs_net_position_weight_column
        )
        if spec.rules.portfolio.max_group_abs_net_position_weight_column is not None
        else None,
        "_portfolio_group": row.get(spec.rules.portfolio.group_column)
        if spec.rules.portfolio.group_column is not None
        else None,
        "_portfolio_turnover_weight": row.get(spec.rules.portfolio.turnover_weight_column)
        if spec.rules.portfolio.turnover_weight_column is not None
        else None,
        "reason_codes": effective_reason_codes,
        "block_reasons": [],
    }


def _multi_leg_signal_rows(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    bindings: dict[str, SymbolBinding],
    base_side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
) -> list[dict[str, Any]]:
    base_weight = _sizing_value(
        row,
        fixed=_signal_position_weight(row, spec),
        column=None,
    )
    base_notional = _sizing_value(
        row,
        fixed=_signal_notional_usd(row, spec),
        column=None,
    )
    rows: list[dict[str, Any]] = []
    group_id = _multi_leg_group_id(spec, row, base_side=base_side)
    leg_count = len(spec.rules.multi_leg.legs)
    anchor_symbol = spec.rules.multi_leg.anchor_real_market_symbol
    for index, leg in enumerate(spec.rules.multi_leg.legs):
        binding = bindings[leg.real_market_symbol]
        leg_side = _resolve_leg_side(base_side, leg.side)
        leg_weight_multiplier = _sizing_value(
            row,
            fixed=leg.position_weight,
            column=leg.position_weight_column,
        )
        leg_weight = (base_weight if base_weight is not None else 1.0) * (
            leg_weight_multiplier if leg_weight_multiplier is not None else 1.0
        )
        leg_notional = _sizing_value(
            row,
            fixed=leg.notional_usd,
            column=leg.notional_usd_column,
        )
        if leg_notional is None and base_notional is not None:
            leg_notional = base_notional * (
                leg_weight_multiplier if leg_weight_multiplier is not None else leg.position_weight
            )
        exit_overrides: dict[str, float | None] = {}
        for field_name in (
            "stop_loss_bps",
            "min_stop_loss_bps",
            "max_stop_loss_bps",
            "take_profit_bps",
            "min_take_profit_bps",
            "max_take_profit_bps",
            "trailing_stop_bps",
            "trailing_stop_activation_bps",
            "partial_take_profit_bps",
        ):
            value = _non_negative_bps_value(
                row,
                fixed=getattr(leg, field_name),
                column=getattr(leg, f"{field_name}_column"),
                field_name=f"rules.multi_leg.legs[].{field_name}",
            )
            if value is not None:
                exit_overrides[field_name] = value
        partial_exit_fraction = _unit_interval_value(
            row,
            fixed=leg.partial_exit_fraction,
            column=leg.partial_exit_fraction_column,
            field_name="rules.multi_leg.legs[].partial_exit_fraction",
        )
        if partial_exit_fraction is not None:
            exit_overrides["partial_exit_fraction"] = partial_exit_fraction
        min_reward_risk_ratio = _non_negative_value(
            row,
            fixed=leg.min_reward_risk_ratio,
            column=leg.min_reward_risk_ratio_column,
            field_name="rules.multi_leg.legs[].min_reward_risk_ratio",
        )
        if min_reward_risk_ratio is not None:
            exit_overrides["min_reward_risk_ratio"] = min_reward_risk_ratio
        order_overrides: dict[str, Any] = {}
        if leg.entry_type is not None or leg.entry_type_column is not None:
            order_overrides["entry_type"] = _entry_type_value(
                row,
                fixed=leg.entry_type or spec.rules.order.entry_type,
                column=leg.entry_type_column,
            )
        for field_name in ("limit_offset_bps", "stop_offset_bps"):
            value = _non_negative_bps_value(
                row,
                fixed=getattr(leg, field_name),
                column=getattr(leg, f"{field_name}_column"),
                field_name=f"rules.multi_leg.legs[].{field_name}",
            )
            if value is not None:
                order_overrides[field_name] = value
        timeout_minutes = _minutes_value(
            row,
            fixed=leg.timeout_minutes,
            column=leg.timeout_minutes_column,
        )
        if timeout_minutes is not None:
            order_overrides["timeout_minutes"] = timeout_minutes
        if leg.time_in_force is not None or leg.time_in_force_column is not None:
            order_overrides["time_in_force"] = _time_in_force_value(
                row,
                fixed=leg.time_in_force or spec.rules.order.time_in_force,
                column=leg.time_in_force_column,
            )
        for field_name in ("post_only", "reduce_only"):
            column_value = _optional_bool_from_row(row, getattr(leg, f"{field_name}_column"))
            fixed_value = getattr(leg, field_name)
            value = column_value if column_value is not None else fixed_value
            if value is not None:
                order_overrides[field_name] = value
        execution_overrides: dict[str, Any] = {}
        for field_name in (
            "slippage_bps",
            "max_spread_bps",
            "min_depth_usd",
            "max_latency_ms",
            "max_borrow_cost_bps",
            "max_tax_drag_bps",
            "max_turnover_pressure",
            "max_capacity_usage_ratio",
            "max_correlation_crowding_score",
        ):
            value = _non_negative_value(
                row,
                fixed=getattr(leg, field_name),
                column=getattr(leg, f"{field_name}_column"),
                field_name=f"rules.multi_leg.legs[].{field_name}",
            )
            if value is not None:
                execution_overrides[field_name] = value
        for field_name in (
            "max_fill_fraction",
            "min_fill_fraction",
            "depth_participation_rate",
            "min_queue_position_score",
            "min_borrow_availability_ratio",
        ):
            value = _unit_interval_value(
                row,
                fixed=getattr(leg, field_name),
                column=getattr(leg, f"{field_name}_column", None),
                field_name=f"rules.multi_leg.legs[].{field_name}",
            )
            if value is not None:
                execution_overrides[field_name] = value
        min_fee_edge_bps = _sizing_value(
            row,
            fixed=leg.min_fee_edge_bps,
            column=leg.min_fee_edge_bps_column,
        )
        if min_fee_edge_bps is not None:
            execution_overrides["min_fee_edge_bps"] = min_fee_edge_bps
        for field_name in (
            "depth_column",
            "latency_column",
            "queue_position_score_column",
            "borrow_availability_column",
            "borrow_cost_column",
            "tax_drag_column",
            "turnover_pressure_column",
            "capacity_usage_column",
            "correlation_crowding_column",
            "fee_edge_column",
        ):
            value = getattr(leg, field_name)
            if value is not None:
                execution_overrides[field_name] = value
        rows.append(
            _trade_signal_row(
                spec=spec,
                row=row,
                binding=binding,
                side=leg_side,
                generated_at=generated_at,
                raw_score=raw_score,
                rank=rank,
                position_weight=leg_weight,
                notional_usd=leg_notional,
                exit_overrides=exit_overrides,
                order_overrides=order_overrides,
                execution_overrides=execution_overrides,
                multi_leg_group_id=group_id,
                multi_leg_leg_index=index + 1,
                multi_leg_leg_count=leg_count,
                multi_leg_anchor_real_market_symbol=anchor_symbol,
                reason_codes=[
                    spec.rules.reason_code,
                    "multi_leg",
                    leg.reason_code or f"leg_{index + 1}",
                ],
            )
        )
    return rows


def build_authoring_signals(
    spec: StrategyAuthoringSpec, *, data_dir: Path
) -> tuple[pl.DataFrame, StrategySignalManifest]:
    errors = validate_authoring_inputs(spec, data_dir=data_dir)
    if errors:
        raise StrategyAuthoringValidationError("; ".join(errors))
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    feature = _apply_condition_features(
        _apply_derived_features(
            _apply_confirmation_panels(pl.read_parquet(feature_path), spec, data_dir=data_dir),
            spec,
        ),
        spec,
    )
    bindings = {binding.real_market_symbol: binding for binding in spec.experiment.symbol_bindings}
    rows: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc)
    risk_throttle_cooldown_until_by_symbol: dict[str, datetime] = {}
    for row in feature.sort(["canonical_symbol", "ts"]).to_dicts():
        symbol = str(row.get("canonical_symbol") or "").upper()
        if (
            spec.rules.multi_leg.enabled
            and symbol != spec.rules.multi_leg.anchor_real_market_symbol
        ):
            continue
        binding = bindings.get(symbol)
        if binding is None:
            continue
        if spec.rules.close is not None and _entry_passes(row, spec.rules.close):
            rows.append(
                _close_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.reduce is not None and _entry_passes(row, spec.rules.reduce):
            rows.append(
                _reduce_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.add is not None and _entry_passes(row, spec.rules.add):
            rows.append(
                _add_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.rebalance is not None and _entry_passes(row, spec.rules.rebalance):
            rows.append(
                _rebalance_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.hold is not None and _entry_passes(row, spec.rules.hold):
            rows.append(
                {
                    "schema_version": "strategy_signal.v1",
                    "signal_id": _signal_id(spec, row, binding, side="none"),
                    "generated_at": generated_at,
                    "strategy_id": spec.experiment.strategy_id,
                    "strategy_family": spec.experiment.strategy_family,
                    "strategy_version": spec.experiment.strategy_version,
                    "trial_id": None,
                    "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
                    "ts_signal": row["ts"],
                    "timeframe": spec.rules.timeframe,
                    "execution_venue": binding.execution_venue,
                    "execution_symbol": binding.execution_symbol,
                    "real_market_symbol": binding.real_market_symbol,
                    "side": "none",
                    "raw_score": None,
                    "rank_score": None,
                    "percentile_rank": None,
                    "tail_bucket": "none",
                    "confidence": 0.0,
                    "source_confidence": row.get("source_confidence"),
                    "venue_quality_score": row.get("venue_quality_score"),
                    "feature_snapshot_ref": None,
                    "quote_ref": None,
                    "tracking_ref": None,
                    "stop_loss_bps": None,
                    "min_stop_loss_bps": None,
                    "max_stop_loss_bps": None,
                    "take_profit_bps": None,
                    "min_take_profit_bps": None,
                    "max_take_profit_bps": None,
                    "min_reward_risk_ratio": None,
                    "reward_risk_ratio": None,
                    "trailing_stop_bps": None,
                    "trailing_stop_activation_bps": None,
                    "partial_take_profit_bps": None,
                    "partial_exit_fraction": None,
                    "min_holding_minutes": None,
                    "max_holding_minutes": None,
                    "exit_priority": DEFAULT_EXIT_PRIORITY,
                    "exit_on_opposite_signal": False,
                    "exit_on_close_signal": False,
                    "exit_on_reduce_signal": False,
                    "reduce_fraction": None,
                    "exit_on_add_signal": False,
                    "add_fraction": None,
                    "exit_on_rebalance_signal": False,
                    "rebalance_target_fraction": None,
                    "rebalance_min_delta_fraction": None,
                    "bracket_type": "none",
                    "bracket_time_stop_minutes": None,
                    "bracket_break_even_after_bps": None,
                    "bracket_break_even_after_partial_take_profit": False,
                    "entry_order_type": "market",
                    "entry_limit_offset_bps": None,
                    "entry_stop_offset_bps": None,
                    "entry_timeout_minutes": None,
                    "entry_time_in_force": "gtc",
                    "entry_post_only": False,
                    "entry_reduce_only": False,
                    "slippage_bps": 0.0,
                    "max_fill_fraction": 0.0,
                    "min_fill_fraction": None,
                    "max_spread_bps": None,
                    "min_depth_usd": None,
                    "depth_column": None,
                    "depth_participation_rate": 0.0,
                    "max_latency_ms": None,
                    "latency_ms": None,
                    "min_queue_position_score": None,
                    "queue_position_score": None,
                    "min_borrow_availability_ratio": None,
                    "borrow_availability_ratio": None,
                    "max_borrow_cost_bps": None,
                    "borrow_cost_bps": None,
                    "max_tax_drag_bps": None,
                    "tax_drag_bps": None,
                    "max_turnover_pressure": None,
                    "turnover_pressure": None,
                    "max_capacity_usage_ratio": None,
                    "capacity_usage_ratio": None,
                    "max_correlation_crowding_score": None,
                    "correlation_crowding_score": None,
                    "min_fee_edge_bps": None,
                    "fee_edge_bps": None,
                    "position_weight": 0.0,
                    "notional_usd": None,
                    "reason_codes": [spec.rules.hold_reason_code],
                    "block_reasons": ["hold_rule"],
                }
            )
            continue
        signal_side, block_reason = _selected_side(row, spec.rules)
        if signal_side is None:
            continue
        if signal_side == "none":
            rows.append(
                {
                    "schema_version": "strategy_signal.v1",
                    "signal_id": _signal_id(spec, row, binding, side="none"),
                    "generated_at": generated_at,
                    "strategy_id": spec.experiment.strategy_id,
                    "strategy_family": spec.experiment.strategy_family,
                    "strategy_version": spec.experiment.strategy_version,
                    "trial_id": None,
                    "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
                    "ts_signal": row["ts"],
                    "timeframe": spec.rules.timeframe,
                    "execution_venue": binding.execution_venue,
                    "execution_symbol": binding.execution_symbol,
                    "real_market_symbol": binding.real_market_symbol,
                    "side": "none",
                    "raw_score": None,
                    "rank_score": None,
                    "percentile_rank": None,
                    "tail_bucket": "none",
                    "confidence": 0.0,
                    "source_confidence": row.get("source_confidence"),
                    "venue_quality_score": row.get("venue_quality_score"),
                    "feature_snapshot_ref": None,
                    "quote_ref": None,
                    "tracking_ref": None,
                    "stop_loss_bps": None,
                    "min_stop_loss_bps": None,
                    "max_stop_loss_bps": None,
                    "take_profit_bps": None,
                    "min_take_profit_bps": None,
                    "max_take_profit_bps": None,
                    "min_reward_risk_ratio": None,
                    "reward_risk_ratio": None,
                    "trailing_stop_bps": None,
                    "trailing_stop_activation_bps": None,
                    "partial_take_profit_bps": None,
                    "partial_exit_fraction": None,
                    "min_holding_minutes": None,
                    "max_holding_minutes": None,
                    "exit_priority": DEFAULT_EXIT_PRIORITY,
                    "exit_on_opposite_signal": False,
                    "exit_on_close_signal": False,
                    "exit_on_reduce_signal": False,
                    "reduce_fraction": None,
                    "exit_on_add_signal": False,
                    "add_fraction": None,
                    "exit_on_rebalance_signal": False,
                    "rebalance_target_fraction": None,
                    "rebalance_min_delta_fraction": None,
                    "bracket_type": "none",
                    "bracket_time_stop_minutes": None,
                    "bracket_break_even_after_bps": None,
                    "bracket_break_even_after_partial_take_profit": False,
                    "entry_order_type": "market",
                    "entry_limit_offset_bps": None,
                    "entry_stop_offset_bps": None,
                    "entry_timeout_minutes": None,
                    "entry_time_in_force": "gtc",
                    "entry_post_only": False,
                    "entry_reduce_only": False,
                    "slippage_bps": 0.0,
                    "max_fill_fraction": 0.0,
                    "min_fill_fraction": None,
                    "max_spread_bps": None,
                    "min_depth_usd": None,
                    "depth_column": None,
                    "depth_participation_rate": 0.0,
                    "max_latency_ms": None,
                    "latency_ms": None,
                    "min_queue_position_score": None,
                    "queue_position_score": None,
                    "min_borrow_availability_ratio": None,
                    "borrow_availability_ratio": None,
                    "max_borrow_cost_bps": None,
                    "borrow_cost_bps": None,
                    "max_tax_drag_bps": None,
                    "tax_drag_bps": None,
                    "max_turnover_pressure": None,
                    "turnover_pressure": None,
                    "max_capacity_usage_ratio": None,
                    "capacity_usage_ratio": None,
                    "max_correlation_crowding_score": None,
                    "correlation_crowding_score": None,
                    "min_fee_edge_bps": None,
                    "fee_edge_bps": None,
                    "position_weight": 0.0,
                    "notional_usd": None,
                    "reason_codes": [spec.rules.hold_reason_code],
                    "block_reasons": [block_reason or "hold_rule"],
                }
            )
            continue
        raw_score = _score(row, spec.rules.score)
        rank = _rank_score(raw_score)
        event_block_reason = _event_window_block_reason(row, spec)
        if event_block_reason is not None:
            rows.append(
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
                    block_reason=event_block_reason,
                )
            )
            continue
        data_guard_block_reason = _data_guard_block_reason(row, spec)
        if data_guard_block_reason is not None:
            rows.append(
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
                    block_reason=data_guard_block_reason,
                )
            )
            continue
        ts_signal = _feature_timestamp(row)
        cooldown_until = risk_throttle_cooldown_until_by_symbol.get(symbol)
        if cooldown_until is not None and ts_signal < cooldown_until:
            risk_throttle_block_reason = "risk_throttle_cooldown"
        else:
            risk_throttle_block_reason = _risk_throttle_block_reason(row, spec)
        if risk_throttle_block_reason is not None:
            if (
                risk_throttle_block_reason != "risk_throttle_cooldown"
                and spec.rules.risk_throttle.cooldown_minutes is not None
            ):
                risk_throttle_cooldown_until_by_symbol[symbol] = ts_signal + timedelta(
                    minutes=spec.rules.risk_throttle.cooldown_minutes
                )
            rows.append(
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
                    block_reason=risk_throttle_block_reason,
                )
            )
            continue
        if spec.rules.multi_leg.enabled:
            rows.extend(
                _multi_leg_signal_rows(
                    spec=spec,
                    row=row,
                    bindings=bindings,
                    base_side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
        else:
            rows.append(
                _trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
    rows = [_apply_stop_target_width_gate(row, spec) for row in rows]
    rows = [_apply_reward_risk_gate(row, spec) for row in rows]
    rows = _apply_cross_sectional_selection(rows, spec)
    rows = _apply_temporal_selection(rows, spec)
    rows = _apply_position_state_limits(rows, spec)

    if spec.rules.portfolio.max_signals_per_timestamp is not None:
        grouped: dict[Any, list[dict[str, Any]]] = {}
        passthrough: list[dict[str, Any]] = []
        for item in rows:
            if item["side"] == "none":
                passthrough.append(item)
                continue
            grouped.setdefault(item["ts_signal"], []).append(item)
        limited: list[dict[str, Any]] = passthrough[:]
        limit = spec.rules.portfolio.max_signals_per_timestamp
        for timestamp_rows in grouped.values():
            limited.extend(
                sorted(
                    timestamp_rows,
                    key=lambda item: (
                        item.get("rank_score") if item.get("rank_score") is not None else -1.0
                    ),
                    reverse=True,
                )[:limit]
            )
        rows = limited
    rows = _apply_portfolio_allocation(rows, spec)
    rows = _apply_portfolio_turnover_budget(rows, spec)
    rows = _apply_portfolio_exposure_limits(rows, spec)
    rows = sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"]))

    frame = (
        empty_strategy_signal_frame()
        if not rows
        else validate_strategy_signal_frame(
            pl.DataFrame(rows), symbol_bindings=spec.experiment.symbol_bindings
        )
    )
    feature_hash = file_sha256(feature_path)
    run_id = (
        empty_signal_artifact_run_id(
            generator_id="strategy_authoring",
            strategy_id=spec.experiment.strategy_id,
            strategy_family=spec.experiment.strategy_family,
            strategy_version=spec.experiment.strategy_version,
            symbol_bindings=spec.experiment.symbol_bindings,
            feature_panel_sha256=feature_hash,
        )
        if frame.is_empty()
        else signal_artifact_run_id(frame)
    )
    manifest = StrategySignalManifest(
        schema_version="strategy_signal_manifest.v1",
        generated_at=generated_at,
        generator_id="strategy_authoring",
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        symbol_bindings=spec.experiment.symbol_bindings,
        feature_panel_sha256=feature_hash,
        signal_count=frame.height,
        signal_artifact_run_id=run_id,
        generator_parameters={
            "authoring_schema_version": spec.schema_version,
            "reason_code": spec.rules.reason_code,
        },
    )
    return frame, manifest


def write_authoring_signal_artifacts(
    frame: pl.DataFrame, manifest: StrategySignalManifest, *, data_dir: Path
) -> dict[str, Path]:
    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    legacy_out = data_dir / "research/signals.csv"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(parquet_out)
    with jsonl_out.open("w", encoding="utf-8") as handle:
        for row in frame.to_dicts():
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    _legacy_export(frame).write_csv(legacy_out)
    write_strategy_signal_manifest(manifest, strategy_signal_manifest_path(data_dir))
    return {
        "signals_parquet": parquet_out,
        "signals_jsonl": jsonl_out,
        "legacy_csv": legacy_out,
        "manifest": strategy_signal_manifest_path(data_dir),
    }


def strategy_signals_to_research_signals(frame: pl.DataFrame) -> list[ResearchSignal]:
    if frame.is_empty():
        return []
    return [
        ResearchSignal(
            ts_signal=row["ts_signal"],
            canonical_symbol=str(row["execution_symbol"]).upper(),
            side=str(row["side"]).lower(),
            timeframe=str(row["timeframe"]).lower(),
            signal_strength=row.get("raw_score"),
            stop_loss_bps=row.get("stop_loss_bps"),
            min_stop_loss_bps=row.get("min_stop_loss_bps"),
            max_stop_loss_bps=row.get("max_stop_loss_bps"),
            take_profit_bps=row.get("take_profit_bps"),
            min_take_profit_bps=row.get("min_take_profit_bps"),
            max_take_profit_bps=row.get("max_take_profit_bps"),
            min_reward_risk_ratio=row.get("min_reward_risk_ratio"),
            reward_risk_ratio=row.get("reward_risk_ratio"),
            trailing_stop_bps=row.get("trailing_stop_bps"),
            trailing_stop_activation_bps=row.get("trailing_stop_activation_bps"),
            partial_take_profit_bps=row.get("partial_take_profit_bps"),
            partial_exit_fraction=row.get("partial_exit_fraction"),
            min_holding_minutes=row.get("min_holding_minutes"),
            max_holding_minutes=row.get("max_holding_minutes"),
            exit_priority=str(row.get("exit_priority") or ""),
            exit_on_opposite_signal=bool(row.get("exit_on_opposite_signal")),
            exit_on_close_signal=bool(row.get("exit_on_close_signal")),
            exit_on_reduce_signal=bool(row.get("exit_on_reduce_signal")),
            reduce_fraction=row.get("reduce_fraction"),
            exit_on_add_signal=bool(row.get("exit_on_add_signal")),
            add_fraction=row.get("add_fraction"),
            exit_on_rebalance_signal=bool(row.get("exit_on_rebalance_signal")),
            rebalance_target_fraction=row.get("rebalance_target_fraction"),
            rebalance_min_delta_fraction=row.get("rebalance_min_delta_fraction"),
            bracket_type=str(row.get("bracket_type") or "none"),
            bracket_time_stop_minutes=row.get("bracket_time_stop_minutes"),
            bracket_break_even_after_bps=row.get("bracket_break_even_after_bps"),
            bracket_break_even_after_partial_take_profit=bool(
                row.get("bracket_break_even_after_partial_take_profit")
            ),
            entry_order_type=str(row.get("entry_order_type") or "market"),
            entry_limit_offset_bps=row.get("entry_limit_offset_bps"),
            entry_stop_offset_bps=row.get("entry_stop_offset_bps"),
            entry_timeout_minutes=row.get("entry_timeout_minutes"),
            entry_time_in_force=str(row.get("entry_time_in_force") or "gtc"),
            entry_post_only=bool(row.get("entry_post_only")),
            entry_reduce_only=bool(row.get("entry_reduce_only")),
            slippage_bps=row.get("slippage_bps") or 0.0,
            max_fill_fraction=row.get("max_fill_fraction") or 1.0,
            min_fill_fraction=row.get("min_fill_fraction"),
            max_spread_bps=row.get("max_spread_bps"),
            min_depth_usd=row.get("min_depth_usd"),
            depth_column=row.get("depth_column"),
            depth_participation_rate=row.get("depth_participation_rate") or 1.0,
            max_latency_ms=row.get("max_latency_ms"),
            latency_ms=row.get("latency_ms"),
            min_queue_position_score=row.get("min_queue_position_score"),
            queue_position_score=row.get("queue_position_score"),
            min_borrow_availability_ratio=row.get("min_borrow_availability_ratio"),
            borrow_availability_ratio=row.get("borrow_availability_ratio"),
            max_borrow_cost_bps=row.get("max_borrow_cost_bps"),
            borrow_cost_bps=row.get("borrow_cost_bps"),
            max_tax_drag_bps=row.get("max_tax_drag_bps"),
            tax_drag_bps=row.get("tax_drag_bps"),
            max_turnover_pressure=row.get("max_turnover_pressure"),
            turnover_pressure=row.get("turnover_pressure"),
            max_capacity_usage_ratio=row.get("max_capacity_usage_ratio"),
            capacity_usage_ratio=row.get("capacity_usage_ratio"),
            max_correlation_crowding_score=row.get("max_correlation_crowding_score"),
            correlation_crowding_score=row.get("correlation_crowding_score"),
            min_fee_edge_bps=row.get("min_fee_edge_bps"),
            fee_edge_bps=row.get("fee_edge_bps"),
            position_weight=row.get("position_weight") or 1.0,
            notional_usd=row.get("notional_usd"),
            signal_id=str(row.get("signal_id") or "") or None,
            multi_leg_group_id=str(row.get("multi_leg_group_id") or "") or None,
            multi_leg_leg_index=row.get("multi_leg_leg_index"),
            multi_leg_leg_count=row.get("multi_leg_leg_count"),
            multi_leg_anchor_real_market_symbol=(
                str(row.get("multi_leg_anchor_real_market_symbol") or "") or None
            ),
        )
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower()
        in {"long", "short", "close", "reduce", "add", "rebalance"}
    ]


def write_authoring_paper_preview_outputs(
    spec: StrategyAuthoringSpec,
    frame: pl.DataFrame,
    summary: dict[str, Any],
    *,
    data_dir: Path,
) -> dict[str, Path]:
    from sis.research.strategy_lab.authoring.scorecard import _paper_preview_scorecard_summary

    now = datetime.now(timezone.utc)
    parameter_hash = _stable_digest(spec.model_dump(mode="json"))
    run_id = signal_artifact_run_id(frame) if not frame.is_empty() else parameter_hash
    trial_id = f"trial-{run_id}"
    trial_group_id = f"trial-group-{run_id}"
    scorecard_summary = _paper_preview_scorecard_summary(summary)
    selected_rows = [
        row
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower() in {"long", "short"}
        and not list(row.get("block_reasons") or [])
    ][:1]
    selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
    selected = bool(selected_signal_ids) and bool(summary.get("backtest_passed", False))
    record = TrialRecord(
        schema_version="trial_record.v1",
        trial_id=trial_id,
        trial_group_id=trial_group_id,
        trial_index=0,
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        parameter_hash=parameter_hash,
        parameter_count=1,
        parameter_space_hash="strategy-authoring-yaml-v1",
        random_seed=None,
        git_sha=None,
        signal_count=frame.height,
        candidate_count=frame.height,
        paper_candidate_count=len(selected_signal_ids) if selected else 0,
        executed_count=0,
        blocked_count=0 if selected else 1,
        no_signal_count=0 if selected_signal_ids else 1,
        blocked_reason_counts={} if selected else {"not_selected": 1},
        metrics={**summary, "selected_signal_ids": selected_signal_ids if selected else []},
        baseline_strategy_id=None,
        baseline_delta_metrics={},
        selected_for_next_stage=selected,
        rejection_reasons=[] if selected else ["insufficient_trades_or_no_signal"],
    )
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    ledger = TrialLedger(ledger_path)
    existing_ids = {item.trial_id for item in ledger.read_all()}
    if record.trial_id not in existing_ids:
        ledger.append(record)

    candidates: list[TradeCandidate] = []
    selected_candidate_ids: list[str] = []
    rejected_candidate_ids: list[str] = []
    rows_for_candidates = selected_rows if selected_rows else [{}]
    for row in rows_for_candidates:
        candidate_id = (
            f"candidate-{trial_id}-{row['signal_id']}" if row else f"candidate-{trial_id}-no-signal"
        )
        status = "candidate" if selected else ("no_signal" if not row else "hold")
        binding = spec.experiment.symbol_bindings[0]
        execution_venue = cast(
            Literal["trade_xyz"], row.get("execution_venue") if row else binding.execution_venue
        )
        side = cast(
            Literal["long", "short", "none"], row.get("side") if selected and row else "none"
        )
        entry_order_type = cast(
            Literal["market", "limit", "stop_market"],
            row.get("entry_order_type") if selected and row else "market",
        )
        tail_bucket = cast(
            Literal["top", "middle", "bottom", "none"],
            row.get("tail_bucket") if selected and row else "none",
        )
        confidence = _float_or_default(row.get("confidence") if selected and row else None, 0.0)
        candidate = TradeCandidate(
            schema_version="trade_candidate.v1",
            candidate_id=candidate_id,
            generated_at=now,
            signal_id=str(row.get("signal_id")) if row else None,
            strategy_id=spec.experiment.strategy_id,
            trial_id=trial_id,
            execution_venue=execution_venue,
            execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
            real_market_symbol=str(row.get("real_market_symbol") or binding.real_market_symbol),
            side=side,
            timeframe=str(row.get("timeframe") or spec.rules.timeframe),
            status=status,
            raw_score=row.get("raw_score") if row else None,
            rank_score=row.get("rank_score") if selected and row else None,
            percentile_rank=row.get("percentile_rank") if selected and row else None,
            tail_bucket=tail_bucket,
            confidence=confidence,
            entry_reason_codes=list(row.get("reason_codes") or []) if selected and row else [],
            block_reasons=[] if selected else record.rejection_reasons,
            stop_loss_bps=row.get("stop_loss_bps") if selected and row else None,
            min_stop_loss_bps=row.get("min_stop_loss_bps") if selected and row else None,
            max_stop_loss_bps=row.get("max_stop_loss_bps") if selected and row else None,
            take_profit_bps=row.get("take_profit_bps") if selected and row else None,
            min_take_profit_bps=row.get("min_take_profit_bps") if selected and row else None,
            max_take_profit_bps=row.get("max_take_profit_bps") if selected and row else None,
            min_reward_risk_ratio=(row.get("min_reward_risk_ratio") if selected and row else None),
            reward_risk_ratio=row.get("reward_risk_ratio") if selected and row else None,
            trailing_stop_bps=row.get("trailing_stop_bps") if selected and row else None,
            trailing_stop_activation_bps=(
                row.get("trailing_stop_activation_bps") if selected and row else None
            ),
            partial_take_profit_bps=(
                row.get("partial_take_profit_bps") if selected and row else None
            ),
            partial_exit_fraction=row.get("partial_exit_fraction") if selected and row else None,
            min_holding_minutes=row.get("min_holding_minutes") if selected and row else None,
            max_holding_minutes=row.get("max_holding_minutes") if selected and row else None,
            exit_priority=str(row.get("exit_priority") or DEFAULT_EXIT_PRIORITY)
            if selected and row
            else DEFAULT_EXIT_PRIORITY,
            exit_on_opposite_signal=(
                bool(row.get("exit_on_opposite_signal")) if selected and row else False
            ),
            bracket_type=cast(
                Literal["none", "oco"], row.get("bracket_type") if selected and row else "none"
            ),
            bracket_time_stop_minutes=(
                row.get("bracket_time_stop_minutes") if selected and row else None
            ),
            bracket_break_even_after_bps=(
                row.get("bracket_break_even_after_bps") if selected and row else None
            ),
            bracket_break_even_after_partial_take_profit=(
                bool(row.get("bracket_break_even_after_partial_take_profit"))
                if selected and row
                else False
            ),
            entry_order_type=entry_order_type,
            entry_limit_offset_bps=row.get("entry_limit_offset_bps") if selected and row else None,
            entry_stop_offset_bps=row.get("entry_stop_offset_bps") if selected and row else None,
            entry_timeout_minutes=row.get("entry_timeout_minutes") if selected and row else None,
            entry_time_in_force=(
                cast(
                    Literal["gtc", "gtd", "ioc", "fok"],
                    row.get("entry_time_in_force") if selected and row else "gtc",
                )
            ),
            entry_post_only=bool(row.get("entry_post_only")) if selected and row else False,
            entry_reduce_only=bool(row.get("entry_reduce_only")) if selected and row else False,
            slippage_bps=_float_or_default(
                row.get("slippage_bps") if selected and row else None,
                0.0,
            ),
            max_fill_fraction=_float_or_default(
                row.get("max_fill_fraction") if selected and row else None,
                0.0,
            ),
            min_fill_fraction=row.get("min_fill_fraction") if selected and row else None,
            max_spread_bps=row.get("max_spread_bps") if selected and row else None,
            min_depth_usd=row.get("min_depth_usd") if selected and row else None,
            depth_column=row.get("depth_column") if selected and row else None,
            depth_participation_rate=_float_or_default(
                row.get("depth_participation_rate") if selected and row else None,
                0.0,
            ),
            max_latency_ms=row.get("max_latency_ms") if selected and row else None,
            latency_ms=row.get("latency_ms") if selected and row else None,
            min_queue_position_score=(
                row.get("min_queue_position_score") if selected and row else None
            ),
            queue_position_score=row.get("queue_position_score") if selected and row else None,
            min_borrow_availability_ratio=(
                row.get("min_borrow_availability_ratio") if selected and row else None
            ),
            borrow_availability_ratio=(
                row.get("borrow_availability_ratio") if selected and row else None
            ),
            max_borrow_cost_bps=row.get("max_borrow_cost_bps") if selected and row else None,
            borrow_cost_bps=row.get("borrow_cost_bps") if selected and row else None,
            max_tax_drag_bps=row.get("max_tax_drag_bps") if selected and row else None,
            tax_drag_bps=row.get("tax_drag_bps") if selected and row else None,
            max_turnover_pressure=(row.get("max_turnover_pressure") if selected and row else None),
            turnover_pressure=row.get("turnover_pressure") if selected and row else None,
            max_capacity_usage_ratio=(
                row.get("max_capacity_usage_ratio") if selected and row else None
            ),
            capacity_usage_ratio=row.get("capacity_usage_ratio") if selected and row else None,
            max_correlation_crowding_score=(
                row.get("max_correlation_crowding_score") if selected and row else None
            ),
            correlation_crowding_score=(
                row.get("correlation_crowding_score") if selected and row else None
            ),
            min_fee_edge_bps=row.get("min_fee_edge_bps") if selected and row else None,
            fee_edge_bps=row.get("fee_edge_bps") if selected and row else None,
            position_weight=row.get("position_weight") if selected and row else None,
            notional_usd=row.get("notional_usd") if selected and row else None,
            feature_snapshot_ref=row.get("feature_snapshot_ref") if row else None,
            quote_ref=row.get("quote_ref") if row else None,
            tracking_ref=row.get("tracking_ref") if row else None,
        )
        candidates.append(candidate)
        (selected_candidate_ids if selected else rejected_candidate_ids).append(candidate_id)

    pack = PaperCandidatePack(
        schema_version="paper_candidate_pack.v1",
        pack_id=f"paper-pack-{run_id}",
        generated_at=now,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        trial_group_id=trial_group_id,
        candidates=candidates,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        selection_policy={
            "source": "strategy_authoring",
            "default_decision": spec.promotion.default_decision,
        },
        reason_codes=["strategy_authoring_v1"],
        block_reasons=[] if selected else record.rejection_reasons,
    )
    pack_path = data_dir / "research/paper_candidate_pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")

    decision = PromotionDecision(
        schema_version="promotion_decision.v1",
        promotion_id=f"promotion-{run_id}",
        generated_at=now,
        source_pack_id=pack.pack_id,
        reviewer=None,
        from_stage="strategy_lab",
        to_stage="paper_observation",
        decision=spec.promotion.default_decision,
        required_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        observed_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        approval_reasons=[],
        rejection_reasons=["operator_review_required"],
        scorecard_summary=scorecard_summary,
    )
    decision_path = data_dir / "research/promotion_decision.json"
    decision_path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    intents: list[PaperIntentPreview] = []
    preview_path = data_dir / "bot/paper_intent_preview.json"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        json.dumps([intent.model_dump(mode="json") for intent in intents], indent=2),
        encoding="utf-8",
    )
    report_path = data_dir / "reports/paper_intent_preview.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Paper Intent Preview\n\n"
        "- source: strategy_authoring\n"
        f"- decision: {decision.decision}\n"
        f"- intents: {len(intents)}\n"
        f"- scorecard_schema_version: {scorecard_summary.get('schema_version')}\n"
        f"- scorecard_failed_thresholds: {scorecard_summary.get('failed_thresholds', [])}\n"
        "- paper_only: true\n",
        encoding="utf-8",
    )
    return {
        "trial_ledger": ledger_path,
        "paper_candidate_pack": pack_path,
        "promotion_decision": decision_path,
        "paper_intent_preview": preview_path,
        "paper_intent_preview_report": report_path,
    }


def write_authoring_run_summary(
    spec: StrategyAuthoringSpec,
    *,
    data_dir: Path,
    through: str,
    artifacts: dict[str, Path],
    signal_count: int,
) -> Path:
    out = data_dir / "research/strategy_authoring_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_run.v1",
                "strategy_id": spec.experiment.strategy_id,
                "through": through,
                "signal_count": signal_count,
                "paper_only": True,
                "live_order_submitted": False,
                "artifacts": {key: str(value) for key, value in artifacts.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out
