from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Literal, cast

from sis.research.strategy_lab.authoring.contracts.base import (
    DEFAULT_EXIT_PRIORITY,
    _stable_digest,
)
from sis.research.strategy_lab.authoring.contracts.core import EntryRules, ScoreRules
from sis.research.strategy_lab.authoring.contracts.multi_leg import RegimeOverride
from sis.research.strategy_lab.authoring.contracts.spec import (
    AuthoringRules,
    StrategyAuthoringSpec,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.features import _condition_passes
from sis.research.strategy_lab.specs import SymbolBinding


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


def _position_weight_value(row: dict[str, Any]) -> float:
    value = row.get("position_weight")
    return float(value) if isinstance(value, int | float) else 1.0


def _portfolio_turnover_weight_value(row: dict[str, Any]) -> float:
    value = row.get("_portfolio_turnover_weight")
    if isinstance(value, int | float):
        return abs(float(value))
    return abs(_position_weight_value(row))
