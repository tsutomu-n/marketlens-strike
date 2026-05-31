from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.common import (
    _entry_type_value,
    _exit_bps,
    _exit_override,
    _exit_override_column,
    _matching_regime_override,
    _minutes_value,
    _non_negative_bps_value,
    _optional_bool_from_row,
    _optional_float_from_row,
    _override_column,
    _override_value,
    _regime_value,
    _signal_id,
    _signal_notional_usd,
    _signal_position_weight,
    _sizing_value,
    _stable_digest,
    _tail_bucket,
    _time_in_force_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


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
