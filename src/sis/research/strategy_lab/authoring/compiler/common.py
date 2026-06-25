from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.contracts.base import (
    DEFAULT_EXIT_PRIORITY,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _optional_float_from_row,
    _sizing_value,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _compiled_signal_id
from sis.research.strategy_lab.authoring.compiler.signal_selection import _entry_passes
from sis.research.strategy_lab.authoring.contracts.multi_leg import RegimeOverride
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


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


def _signal_timestamp(row: dict[str, Any]) -> datetime:
    value = row["ts_signal"]
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise StrategyAuthoringValidationError(f"Unsupported ts_signal value: {value!r}")


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
