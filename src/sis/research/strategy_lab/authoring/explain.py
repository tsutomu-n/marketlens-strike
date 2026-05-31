from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.authoring.contracts.core import Condition
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.validation import (
    _required_columns,
    _resolve_path,
    validate_authoring_inputs,
)


def _format_condition(condition: Condition) -> str:
    target = (
        f"column:{condition.value_column}"
        if condition.value_column is not None
        else repr(condition.value)
    )
    if condition.op in {"is_true", "is_false", "rising", "falling"}:
        return f"{condition.column} {condition.op}"
    return f"{condition.column} {condition.op} {target}"


def explain_authoring_spec(spec: StrategyAuthoringSpec, *, data_dir: Path) -> str:
    errors = validate_authoring_inputs(spec, data_dir=data_dir)
    required_columns = sorted(_required_columns(spec))
    bindings = ", ".join(
        f"{item.real_market_symbol}->{item.execution_symbol}@{item.execution_venue}"
        for item in spec.experiment.symbol_bindings
    )
    conditions = [*spec.rules.entry.all, *spec.rules.entry.any, *spec.rules.entry.none]
    long_conditions = (
        [*spec.rules.long_entry.all, *spec.rules.long_entry.any, *spec.rules.long_entry.none]
        if spec.rules.long_entry is not None
        else []
    )
    short_conditions = (
        [*spec.rules.short_entry.all, *spec.rules.short_entry.any, *spec.rules.short_entry.none]
        if spec.rules.short_entry is not None
        else []
    )
    hold_conditions = (
        [*spec.rules.hold.all, *spec.rules.hold.any, *spec.rules.hold.none]
        if spec.rules.hold is not None
        else []
    )
    close_conditions = (
        [*spec.rules.close.all, *spec.rules.close.any, *spec.rules.close.none]
        if spec.rules.close is not None
        else []
    )
    reduce_conditions = (
        [*spec.rules.reduce.all, *spec.rules.reduce.any, *spec.rules.reduce.none]
        if spec.rules.reduce is not None
        else []
    )
    add_conditions = (
        [*spec.rules.add.all, *spec.rules.add.any, *spec.rules.add.none]
        if spec.rules.add is not None
        else []
    )
    rebalance_conditions = (
        [*spec.rules.rebalance.all, *spec.rules.rebalance.any, *spec.rules.rebalance.none]
        if spec.rules.rebalance is not None
        else []
    )
    condition_lines = "\n".join(f"- {_format_condition(condition)}" for condition in conditions)
    score_lines = (
        "\n".join(f"- {term.column} * {term.weight}" for term in spec.rules.score.weighted_sum)
        or "- no weighted_sum terms"
    )
    if spec.rules.score.model_score is not None:
        model = spec.rules.score.model_score
        model_lines = "\n".join(f"- {term.column} * {term.weight}" for term in model.coefficients)
        score_lines += (
            "\n"
            f"- model_score.type: {model.model_type}\n"
            f"- model_score.intercept: {model.intercept}\n"
            f"- model_score.activation: {model.activation}\n"
            f"- model_score.missing_value: {model.missing_value}\n"
            f"{model_lines}"
        )
    if not spec.rules.score.enabled:
        score_lines = "- no score; raw/rank score will be null"
    hold_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in hold_conditions
        )
        or "- no hold rules"
    )
    close_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in close_conditions
        )
        or "- no close rules"
    )
    reduce_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in reduce_conditions
        )
        or "- no reduce rules"
    )
    add_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in add_conditions
        )
        or "- no add rules"
    )
    rebalance_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in rebalance_conditions
        )
        or "- no rebalance rules"
    )
    long_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in long_conditions
        )
        or "- no long-specific rules"
    )
    short_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in short_conditions
        )
        or "- no short-specific rules"
    )
    multi_leg_lines = "- disabled"
    if spec.rules.multi_leg.enabled:
        multi_leg_lines = "\n".join(
            (
                f"- {leg.real_market_symbol} side={leg.side} "
                f"position_weight={leg.position_weight} "
                f"position_weight_column={leg.position_weight_column} "
                f"notional_usd={leg.notional_usd} "
                f"notional_usd_column={leg.notional_usd_column} "
                f"stop_loss_bps={leg.stop_loss_bps} "
                f"stop_loss_bps_column={leg.stop_loss_bps_column} "
                f"take_profit_bps={leg.take_profit_bps} "
                f"take_profit_bps_column={leg.take_profit_bps_column} "
                f"trailing_stop_bps={leg.trailing_stop_bps} "
                f"trailing_stop_bps_column={leg.trailing_stop_bps_column} "
                f"partial_take_profit_bps={leg.partial_take_profit_bps} "
                f"partial_take_profit_bps_column={leg.partial_take_profit_bps_column} "
                f"partial_exit_fraction={leg.partial_exit_fraction} "
                f"partial_exit_fraction_column={leg.partial_exit_fraction_column} "
                f"min_reward_risk_ratio={leg.min_reward_risk_ratio} "
                f"min_reward_risk_ratio_column={leg.min_reward_risk_ratio_column} "
                f"entry_type={leg.entry_type} "
                f"entry_type_column={leg.entry_type_column} "
                f"limit_offset_bps={leg.limit_offset_bps} "
                f"limit_offset_bps_column={leg.limit_offset_bps_column} "
                f"stop_offset_bps={leg.stop_offset_bps} "
                f"stop_offset_bps_column={leg.stop_offset_bps_column} "
                f"time_in_force={leg.time_in_force} "
                f"time_in_force_column={leg.time_in_force_column} "
                f"timeout_minutes={leg.timeout_minutes} "
                f"timeout_minutes_column={leg.timeout_minutes_column} "
                f"post_only={leg.post_only} "
                f"post_only_column={leg.post_only_column} "
                f"reduce_only={leg.reduce_only} "
                f"reduce_only_column={leg.reduce_only_column} "
                f"slippage_bps={leg.slippage_bps} "
                f"slippage_bps_column={leg.slippage_bps_column} "
                f"max_fill_fraction={leg.max_fill_fraction} "
                f"max_fill_fraction_column={leg.max_fill_fraction_column} "
                f"min_fill_fraction={leg.min_fill_fraction} "
                f"min_fill_fraction_column={leg.min_fill_fraction_column} "
                f"max_spread_bps={leg.max_spread_bps} "
                f"max_spread_bps_column={leg.max_spread_bps_column} "
                f"min_depth_usd={leg.min_depth_usd} "
                f"min_depth_usd_column={leg.min_depth_usd_column} "
                f"depth_column={leg.depth_column} "
                f"depth_participation_rate={leg.depth_participation_rate} "
                f"max_latency_ms={leg.max_latency_ms} "
                f"max_latency_ms_column={leg.max_latency_ms_column} "
                f"latency_column={leg.latency_column} "
                f"min_queue_position_score={leg.min_queue_position_score} "
                f"min_queue_position_score_column={leg.min_queue_position_score_column} "
                f"queue_position_score_column={leg.queue_position_score_column} "
                f"min_borrow_availability_ratio={leg.min_borrow_availability_ratio} "
                f"min_borrow_availability_ratio_column={leg.min_borrow_availability_ratio_column} "
                f"borrow_availability_column={leg.borrow_availability_column} "
                f"max_borrow_cost_bps={leg.max_borrow_cost_bps} "
                f"max_borrow_cost_bps_column={leg.max_borrow_cost_bps_column} "
                f"borrow_cost_column={leg.borrow_cost_column} "
                f"max_tax_drag_bps={leg.max_tax_drag_bps} "
                f"max_tax_drag_bps_column={leg.max_tax_drag_bps_column} "
                f"tax_drag_column={leg.tax_drag_column} "
                f"max_turnover_pressure={leg.max_turnover_pressure} "
                f"max_turnover_pressure_column={leg.max_turnover_pressure_column} "
                f"turnover_pressure_column={leg.turnover_pressure_column} "
                f"max_capacity_usage_ratio={leg.max_capacity_usage_ratio} "
                f"max_capacity_usage_ratio_column={leg.max_capacity_usage_ratio_column} "
                f"capacity_usage_column={leg.capacity_usage_column} "
                f"max_correlation_crowding_score={leg.max_correlation_crowding_score} "
                f"max_correlation_crowding_score_column={leg.max_correlation_crowding_score_column} "
                f"correlation_crowding_column={leg.correlation_crowding_column} "
                f"min_fee_edge_bps={leg.min_fee_edge_bps} "
                f"min_fee_edge_bps_column={leg.min_fee_edge_bps_column} "
                f"fee_edge_column={leg.fee_edge_column} "
                f"reason_code={leg.reason_code or f'leg_{index + 1}'}"
            )
            for index, leg in enumerate(spec.rules.multi_leg.legs)
        )
    status = "ok" if not errors else "invalid"
    error_lines = "\n".join(f"- {error}" for error in errors) or "- none"
    return (
        "# Strategy Authoring Explain\n\n"
        f"- status: {status}\n"
        f"- schema_version: {spec.schema_version}\n"
        f"- strategy_id: {spec.experiment.strategy_id}\n"
        f"- paper_only: true\n"
        f"- live_order_submitted: false\n"
        f"- symbol_bindings: {bindings}\n"
        f"- side: {spec.rules.side}\n"
        f"- side_column: {spec.rules.side_column}\n"
        f"- timeframe: {spec.rules.timeframe}\n"
        f"- feature_panel_path: {_resolve_path(spec.data.feature_panel_path, data_dir)}\n"
        f"- quote_data_path: {_resolve_path(spec.data.quote_data_path, data_dir)}\n"
        f"- cost_model_path: {_resolve_path(spec.data.cost_model_path, data_dir)}\n"
        "\n## Required Feature Columns\n\n"
        + "\n".join(f"- {column}" for column in required_columns)
        + "\n\n## Entry Conditions\n\n"
        + condition_lines
        + "\n\n## Long Entry Conditions\n\n"
        + long_lines
        + "\n\n## Short Entry Conditions\n\n"
        + short_lines
        + "\n\n## Hold Conditions\n\n"
        + hold_lines
        + "\n\n## Close Conditions\n\n"
        + close_lines
        + "\n\n## Reduce Conditions\n\n"
        + reduce_lines
        + "\n\n## Add Conditions\n\n"
        + add_lines
        + "\n\n## Rebalance Conditions\n\n"
        + rebalance_lines
        + "\n\n## Exit Rules\n\n"
        f"- stop_loss_bps: {spec.rules.exit.stop_loss_bps}\n"
        f"- min_stop_loss_bps: {spec.rules.exit.min_stop_loss_bps}\n"
        f"- min_stop_loss_bps_column: {spec.rules.exit.min_stop_loss_bps_column}\n"
        f"- max_stop_loss_bps: {spec.rules.exit.max_stop_loss_bps}\n"
        f"- max_stop_loss_bps_column: {spec.rules.exit.max_stop_loss_bps_column}\n"
        f"- exit_on_opposite_signal: {spec.rules.exit.exit_on_opposite_signal}\n"
        f"- exit_on_close_signal: {spec.rules.exit.exit_on_close_signal}\n"
        f"- exit_on_reduce_signal: {spec.rules.exit.exit_on_reduce_signal}\n"
        f"- reduce_fraction: {spec.rules.exit.reduce_fraction}\n"
        f"- reduce_fraction_column: {spec.rules.exit.reduce_fraction_column}\n"
        f"- exit_on_add_signal: {spec.rules.exit.exit_on_add_signal}\n"
        f"- add_fraction: {spec.rules.exit.add_fraction}\n"
        f"- add_fraction_column: {spec.rules.exit.add_fraction_column}\n"
        f"- exit_on_rebalance_signal: {spec.rules.exit.exit_on_rebalance_signal}\n"
        f"- rebalance_target_fraction: {spec.rules.exit.rebalance_target_fraction}\n"
        f"- rebalance_target_fraction_column: "
        f"{spec.rules.exit.rebalance_target_fraction_column}\n"
        f"- rebalance_min_delta_fraction: {spec.rules.exit.rebalance_min_delta_fraction}\n"
        f"- rebalance_min_delta_fraction_column: "
        f"{spec.rules.exit.rebalance_min_delta_fraction_column}\n"
        f"- stop_loss_bps_column: {spec.rules.exit.stop_loss_bps_column}\n"
        f"- take_profit_bps: {spec.rules.exit.take_profit_bps}\n"
        f"- min_take_profit_bps: {spec.rules.exit.min_take_profit_bps}\n"
        f"- min_take_profit_bps_column: {spec.rules.exit.min_take_profit_bps_column}\n"
        f"- max_take_profit_bps: {spec.rules.exit.max_take_profit_bps}\n"
        f"- max_take_profit_bps_column: {spec.rules.exit.max_take_profit_bps_column}\n"
        f"- take_profit_bps_column: {spec.rules.exit.take_profit_bps_column}\n"
        f"- min_reward_risk_ratio: {spec.rules.exit.min_reward_risk_ratio}\n"
        f"- min_reward_risk_ratio_column: {spec.rules.exit.min_reward_risk_ratio_column}\n"
        f"- trailing_stop_bps: {spec.rules.exit.trailing_stop_bps}\n"
        f"- trailing_stop_bps_column: {spec.rules.exit.trailing_stop_bps_column}\n"
        f"- trailing_stop_activation_bps: {spec.rules.exit.trailing_stop_activation_bps}\n"
        f"- trailing_stop_activation_bps_column: "
        f"{spec.rules.exit.trailing_stop_activation_bps_column}\n"
        f"- partial_take_profit_bps: {spec.rules.exit.partial_take_profit_bps}\n"
        f"- partial_take_profit_bps_column: {spec.rules.exit.partial_take_profit_bps_column}\n"
        f"- partial_exit_fraction: {spec.rules.exit.partial_exit_fraction}\n"
        f"- partial_exit_fraction_column: {spec.rules.exit.partial_exit_fraction_column}\n"
        f"- min_holding_minutes: {spec.rules.exit.min_holding_minutes}\n"
        f"- min_holding_minutes_column: {spec.rules.exit.min_holding_minutes_column}\n"
        f"- max_holding_minutes: {spec.rules.exit.max_holding_minutes}\n"
        f"- max_holding_minutes_column: {spec.rules.exit.max_holding_minutes_column}\n"
        f"- exit_priority: {spec.rules.exit.exit_priority}\n"
        "\n\n## Bracket / OCO\n\n"
        f"- enabled: {spec.rules.bracket.enabled}\n"
        f"- bracket_type: {spec.rules.bracket.bracket_type if spec.rules.bracket.enabled else 'none'}\n"
        f"- time_stop_minutes: {spec.rules.bracket.time_stop_minutes}\n"
        f"- time_stop_minutes_column: {spec.rules.bracket.time_stop_minutes_column}\n"
        f"- break_even_after_bps: {spec.rules.bracket.break_even_after_bps}\n"
        f"- break_even_after_bps_column: {spec.rules.bracket.break_even_after_bps_column}\n"
        f"- break_even_after_partial_take_profit: "
        f"{spec.rules.bracket.break_even_after_partial_take_profit}\n"
        "\n\n## Sizing\n\n"
        f"- position_weight: {spec.rules.sizing.position_weight}\n"
        f"- position_weight_column: {spec.rules.sizing.position_weight_column}\n"
        f"- notional_usd: {spec.rules.sizing.notional_usd}\n"
        f"- notional_usd_column: {spec.rules.sizing.notional_usd_column}\n"
        "\n\n## Order Simulation\n\n"
        f"- entry_type: {spec.rules.order.entry_type}\n"
        f"- entry_type_column: {spec.rules.order.entry_type_column}\n"
        f"- limit_offset_bps: {spec.rules.order.limit_offset_bps}\n"
        f"- limit_offset_bps_column: {spec.rules.order.limit_offset_bps_column}\n"
        f"- stop_offset_bps: {spec.rules.order.stop_offset_bps}\n"
        f"- stop_offset_bps_column: {spec.rules.order.stop_offset_bps_column}\n"
        f"- timeout_minutes: {spec.rules.order.timeout_minutes}\n"
        f"- timeout_minutes_column: {spec.rules.order.timeout_minutes_column}\n"
        f"- time_in_force: {spec.rules.order.time_in_force}\n"
        f"- time_in_force_column: {spec.rules.order.time_in_force_column}\n"
        f"- post_only: {spec.rules.order.post_only}\n"
        f"- post_only_column: {spec.rules.order.post_only_column}\n"
        f"- reduce_only: {spec.rules.order.reduce_only}\n"
        f"- reduce_only_column: {spec.rules.order.reduce_only_column}\n"
        "\n\n## Execution Quality\n\n"
        f"- slippage_bps: {spec.rules.execution.slippage_bps}\n"
        f"- slippage_bps_column: {spec.rules.execution.slippage_bps_column}\n"
        f"- max_fill_fraction: {spec.rules.execution.max_fill_fraction}\n"
        f"- max_fill_fraction_column: {spec.rules.execution.max_fill_fraction_column}\n"
        f"- min_fill_fraction: {spec.rules.execution.min_fill_fraction}\n"
        f"- min_fill_fraction_column: {spec.rules.execution.min_fill_fraction_column}\n"
        f"- max_spread_bps: {spec.rules.execution.max_spread_bps}\n"
        f"- max_spread_bps_column: {spec.rules.execution.max_spread_bps_column}\n"
        f"- min_depth_usd: {spec.rules.execution.min_depth_usd}\n"
        f"- min_depth_usd_column: {spec.rules.execution.min_depth_usd_column}\n"
        f"- depth_column: {spec.rules.execution.depth_column}\n"
        f"- depth_participation_rate: {spec.rules.execution.depth_participation_rate}\n"
        f"- max_latency_ms: {spec.rules.execution.max_latency_ms}\n"
        f"- max_latency_ms_column: {spec.rules.execution.max_latency_ms_column}\n"
        f"- latency_column: {spec.rules.execution.latency_column}\n"
        f"- min_queue_position_score: {spec.rules.execution.min_queue_position_score}\n"
        f"- min_queue_position_score_column: {spec.rules.execution.min_queue_position_score_column}\n"
        f"- queue_position_score_column: {spec.rules.execution.queue_position_score_column}\n"
        f"- min_borrow_availability_ratio: {spec.rules.execution.min_borrow_availability_ratio}\n"
        f"- min_borrow_availability_ratio_column: {spec.rules.execution.min_borrow_availability_ratio_column}\n"
        f"- borrow_availability_column: {spec.rules.execution.borrow_availability_column}\n"
        f"- max_borrow_cost_bps: {spec.rules.execution.max_borrow_cost_bps}\n"
        f"- max_borrow_cost_bps_column: {spec.rules.execution.max_borrow_cost_bps_column}\n"
        f"- borrow_cost_column: {spec.rules.execution.borrow_cost_column}\n"
        f"- max_tax_drag_bps: {spec.rules.execution.max_tax_drag_bps}\n"
        f"- max_tax_drag_bps_column: {spec.rules.execution.max_tax_drag_bps_column}\n"
        f"- tax_drag_column: {spec.rules.execution.tax_drag_column}\n"
        f"- max_turnover_pressure: {spec.rules.execution.max_turnover_pressure}\n"
        f"- max_turnover_pressure_column: "
        f"{spec.rules.execution.max_turnover_pressure_column}\n"
        f"- turnover_pressure_column: {spec.rules.execution.turnover_pressure_column}\n"
        f"- max_capacity_usage_ratio: {spec.rules.execution.max_capacity_usage_ratio}\n"
        f"- max_capacity_usage_ratio_column: "
        f"{spec.rules.execution.max_capacity_usage_ratio_column}\n"
        f"- capacity_usage_column: {spec.rules.execution.capacity_usage_column}\n"
        f"- max_correlation_crowding_score: {spec.rules.execution.max_correlation_crowding_score}\n"
        f"- max_correlation_crowding_score_column: "
        f"{spec.rules.execution.max_correlation_crowding_score_column}\n"
        f"- correlation_crowding_column: {spec.rules.execution.correlation_crowding_column}\n"
        f"- min_fee_edge_bps: {spec.rules.execution.min_fee_edge_bps}\n"
        f"- min_fee_edge_bps_column: {spec.rules.execution.min_fee_edge_bps_column}\n"
        f"- fee_edge_column: {spec.rules.execution.fee_edge_column}\n"
        "\n\n## Portfolio\n\n"
        f"- max_signals_per_timestamp: {spec.rules.portfolio.max_signals_per_timestamp}\n"
        f"- max_total_position_weight: {spec.rules.portfolio.max_total_position_weight}\n"
        f"- max_total_position_weight_column: "
        f"{spec.rules.portfolio.max_total_position_weight_column}\n"
        f"- max_long_position_weight: {spec.rules.portfolio.max_long_position_weight}\n"
        f"- max_long_position_weight_column: "
        f"{spec.rules.portfolio.max_long_position_weight_column}\n"
        f"- max_short_position_weight: {spec.rules.portfolio.max_short_position_weight}\n"
        f"- max_short_position_weight_column: "
        f"{spec.rules.portfolio.max_short_position_weight_column}\n"
        f"- max_abs_net_position_weight: {spec.rules.portfolio.max_abs_net_position_weight}\n"
        f"- max_abs_net_position_weight_column: "
        f"{spec.rules.portfolio.max_abs_net_position_weight_column}\n"
        f"- max_symbol_position_weight: {spec.rules.portfolio.max_symbol_position_weight}\n"
        f"- max_symbol_position_weight_column: "
        f"{spec.rules.portfolio.max_symbol_position_weight_column}\n"
        f"- max_group_position_weight: {spec.rules.portfolio.max_group_position_weight}\n"
        f"- max_group_position_weight_column: "
        f"{spec.rules.portfolio.max_group_position_weight_column}\n"
        f"- max_group_abs_net_position_weight: "
        f"{spec.rules.portfolio.max_group_abs_net_position_weight}\n"
        f"- max_group_abs_net_position_weight_column: "
        f"{spec.rules.portfolio.max_group_abs_net_position_weight_column}\n"
        f"- allocation_method: {spec.rules.portfolio.allocation_method}\n"
        f"- target_total_position_weight: {spec.rules.portfolio.target_total_position_weight}\n"
        f"- target_total_position_weight_column: "
        f"{spec.rules.portfolio.target_total_position_weight_column}\n"
        f"- allocation_volatility_column: {spec.rules.portfolio.allocation_volatility_column}\n"
        f"- allocation_beta_column: {spec.rules.portfolio.allocation_beta_column}\n"
        f"- max_turnover_weight_per_timestamp: "
        f"{spec.rules.portfolio.max_turnover_weight_per_timestamp}\n"
        f"- turnover_weight_column: {spec.rules.portfolio.turnover_weight_column}\n"
        f"- group_column: {spec.rules.portfolio.group_column}\n"
        "\n\n## Position State\n\n"
        f"- max_open_signals_per_symbol: {spec.rules.position.max_open_signals_per_symbol}\n"
        f"- max_open_position_weight_per_symbol: "
        f"{spec.rules.position.max_open_position_weight_per_symbol}\n"
        f"- holding_horizon_minutes: {spec.rules.position.holding_horizon_minutes}\n"
        f"- require_open_position_for_markers: "
        f"{spec.rules.position.require_open_position_for_markers}\n"
        f"- allow_opposing_open_positions: {spec.rules.position.allow_opposing_open_positions}\n"
        f"- allow_pyramiding: {spec.rules.position.allow_pyramiding}\n"
        "\n\n## Risk Throttle\n\n"
        f"- profile: {spec.rules.risk_throttle.profile}\n"
        f"- max_drawdown_column: {spec.rules.risk_throttle.max_drawdown_column}\n"
        f"- max_drawdown_floor: {spec.rules.risk_throttle.max_drawdown_floor}\n"
        f"- max_drawdown_floor_column: {spec.rules.risk_throttle.max_drawdown_floor_column}\n"
        f"- daily_loss_column: {spec.rules.risk_throttle.daily_loss_column}\n"
        f"- daily_loss_floor: {spec.rules.risk_throttle.daily_loss_floor}\n"
        f"- daily_loss_floor_column: {spec.rules.risk_throttle.daily_loss_floor_column}\n"
        f"- loss_streak_column: {spec.rules.risk_throttle.loss_streak_column}\n"
        f"- max_loss_streak: {spec.rules.risk_throttle.max_loss_streak}\n"
        f"- max_loss_streak_column: {spec.rules.risk_throttle.max_loss_streak_column}\n"
        f"- cooldown_minutes: {spec.rules.risk_throttle.cooldown_minutes}\n"
        "\n\n## Data Guard\n\n"
        f"- profile: {spec.rules.data_guard.profile}\n"
        f"- max_feature_age_minutes: {spec.rules.data_guard.max_feature_age_minutes}\n"
        f"- max_feature_age_minutes_column: "
        f"{spec.rules.data_guard.max_feature_age_minutes_column}\n"
        f"- feature_age_column: {spec.rules.data_guard.feature_age_column}\n"
        f"- min_source_confidence: {spec.rules.data_guard.min_source_confidence}\n"
        f"- min_source_confidence_column: {spec.rules.data_guard.min_source_confidence_column}\n"
        f"- source_confidence_column: {spec.rules.data_guard.source_confidence_column}\n"
        f"- min_venue_quality_score: {spec.rules.data_guard.min_venue_quality_score}\n"
        f"- min_venue_quality_score_column: "
        f"{spec.rules.data_guard.min_venue_quality_score_column}\n"
        f"- venue_quality_score_column: {spec.rules.data_guard.venue_quality_score_column}\n"
        f"- max_staleness_bps: {spec.rules.data_guard.max_staleness_bps}\n"
        f"- max_staleness_bps_column: {spec.rules.data_guard.max_staleness_bps_column}\n"
        f"- staleness_bps_column: {spec.rules.data_guard.staleness_bps_column}\n"
        f"- max_regime_transition_score: "
        f"{spec.rules.data_guard.max_regime_transition_score}\n"
        f"- max_regime_transition_score_column: "
        f"{spec.rules.data_guard.max_regime_transition_score_column}\n"
        f"- regime_transition_score_column: "
        f"{spec.rules.data_guard.regime_transition_score_column}\n"
        "\n\n## Temporal Controls\n\n"
        f"- allowed_weekdays_utc: {spec.rules.temporal.allowed_weekdays_utc}\n"
        f"- allowed_hours_utc: {spec.rules.temporal.allowed_hours_utc}\n"
        f"- cooldown_minutes: {spec.rules.temporal.cooldown_minutes}\n"
        f"- max_signals_per_symbol_per_day: {spec.rules.temporal.max_signals_per_symbol_per_day}\n"
        "\n\n## Cross Sectional Selection\n\n"
        f"- long_top_n: {spec.rules.cross_sectional.long_top_n}\n"
        f"- short_bottom_n: {spec.rules.cross_sectional.short_bottom_n}\n"
        f"- long_top_fraction: {spec.rules.cross_sectional.long_top_fraction}\n"
        f"- short_bottom_fraction: {spec.rules.cross_sectional.short_bottom_fraction}\n"
        f"- group_column: {spec.rules.cross_sectional.group_column}\n"
        f"- min_candidates: {spec.rules.cross_sectional.min_candidates}\n"
        f"- min_long_score: {spec.rules.cross_sectional.min_long_score}\n"
        f"- max_short_score: {spec.rules.cross_sectional.max_short_score}\n"
        "\n\n## Multi-Leg\n\n"
        f"- enabled: {spec.rules.multi_leg.enabled}\n"
        f"- anchor_real_market_symbol: {spec.rules.multi_leg.anchor_real_market_symbol}\n"
        + multi_leg_lines
        + "\n\n## Score\n\n"
        + score_lines
        + "\n\n## Backtest\n\n"
        f"- split_method: {spec.backtest.split_method}\n"
        f"- era_unit: {spec.backtest.era_unit}\n"
        f"- label_horizon_minutes: {spec.backtest.label_horizon_minutes}\n"
        f"- min_trade_count: {spec.backtest.min_trade_count}\n"
        "\n## Validation Errors\n\n" + error_lines + "\n"
    )
