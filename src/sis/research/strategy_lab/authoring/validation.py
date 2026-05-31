from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.research.strategy_lab.authoring.contracts import (
    Condition,
    ConfirmationPanel,
    StrategyAuthoringSpec,
)


def _resolve_path(raw: str, data_dir: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "data":
        return data_dir.parent / path
    return path


def _prefixed_confirmation_columns(panel: ConfirmationPanel, columns: set[str]) -> set[str]:
    return {
        f"{panel.prefix}_{column}" for column in columns if column not in {"ts", "canonical_symbol"}
    }


def _required_columns(spec: StrategyAuthoringSpec) -> set[str]:
    columns = {"ts", "canonical_symbol"}
    derived_names = {feature.name for feature in spec.rules.derived_features}

    def add_column(column: str) -> None:
        if column not in derived_names:
            columns.add(column)

    def add_condition_columns(conditions: list[Condition]) -> None:
        for cond in conditions:
            add_column(cond.column)
            if cond.value_column is not None:
                add_column(cond.value_column)

    for feature in spec.rules.derived_features:
        for column in feature.columns:
            add_column(column)

    add_condition_columns([*spec.rules.entry.all, *spec.rules.entry.any, *spec.rules.entry.none])
    for entry in (spec.rules.long_entry, spec.rules.short_entry):
        if entry is not None:
            add_condition_columns([*entry.all, *entry.any, *entry.none])
    if spec.rules.hold is not None:
        add_condition_columns([*spec.rules.hold.all, *spec.rules.hold.any, *spec.rules.hold.none])
    if spec.rules.close is not None:
        add_condition_columns(
            [*spec.rules.close.all, *spec.rules.close.any, *spec.rules.close.none]
        )
    if spec.rules.reduce is not None:
        add_condition_columns(
            [*spec.rules.reduce.all, *spec.rules.reduce.any, *spec.rules.reduce.none]
        )
    if spec.rules.add is not None:
        add_condition_columns([*spec.rules.add.all, *spec.rules.add.any, *spec.rules.add.none])
    if spec.rules.rebalance is not None:
        add_condition_columns(
            [*spec.rules.rebalance.all, *spec.rules.rebalance.any, *spec.rules.rebalance.none]
        )
    for regime in spec.rules.regime_overrides:
        add_condition_columns([*regime.when.all, *regime.when.any, *regime.when.none])
    for term in spec.rules.score.weighted_sum:
        add_column(term.column)
    if spec.rules.score.model_score is not None:
        for term in spec.rules.score.model_score.coefficients:
            add_column(term.column)
    if spec.rules.side_column is not None:
        add_column(spec.rules.side_column)
    if spec.rules.order.entry_type_column is not None:
        add_column(spec.rules.order.entry_type_column)
    if spec.rules.order.limit_offset_bps_column is not None:
        add_column(spec.rules.order.limit_offset_bps_column)
    if spec.rules.order.stop_offset_bps_column is not None:
        add_column(spec.rules.order.stop_offset_bps_column)
    if spec.rules.order.timeout_minutes_column is not None:
        add_column(spec.rules.order.timeout_minutes_column)
    if spec.rules.order.time_in_force_column is not None:
        add_column(spec.rules.order.time_in_force_column)
    if spec.rules.order.post_only_column is not None:
        add_column(spec.rules.order.post_only_column)
    if spec.rules.order.reduce_only_column is not None:
        add_column(spec.rules.order.reduce_only_column)
    if spec.rules.exit.stop_loss_bps_column is not None:
        columns.add(spec.rules.exit.stop_loss_bps_column)
    if spec.rules.exit.min_stop_loss_bps_column is not None:
        columns.add(spec.rules.exit.min_stop_loss_bps_column)
    if spec.rules.exit.max_stop_loss_bps_column is not None:
        columns.add(spec.rules.exit.max_stop_loss_bps_column)
    if spec.rules.exit.take_profit_bps_column is not None:
        columns.add(spec.rules.exit.take_profit_bps_column)
    if spec.rules.exit.min_take_profit_bps_column is not None:
        columns.add(spec.rules.exit.min_take_profit_bps_column)
    if spec.rules.exit.max_take_profit_bps_column is not None:
        columns.add(spec.rules.exit.max_take_profit_bps_column)
    if spec.rules.exit.min_reward_risk_ratio_column is not None:
        columns.add(spec.rules.exit.min_reward_risk_ratio_column)
    if spec.rules.exit.trailing_stop_bps_column is not None:
        columns.add(spec.rules.exit.trailing_stop_bps_column)
    if spec.rules.exit.trailing_stop_activation_bps_column is not None:
        columns.add(spec.rules.exit.trailing_stop_activation_bps_column)
    if spec.rules.exit.partial_take_profit_bps_column is not None:
        columns.add(spec.rules.exit.partial_take_profit_bps_column)
    if spec.rules.exit.partial_exit_fraction_column is not None:
        columns.add(spec.rules.exit.partial_exit_fraction_column)
    if spec.rules.exit.min_holding_minutes_column is not None:
        columns.add(spec.rules.exit.min_holding_minutes_column)
    if spec.rules.exit.max_holding_minutes_column is not None:
        columns.add(spec.rules.exit.max_holding_minutes_column)
    if spec.rules.exit.reduce_fraction_column is not None:
        columns.add(spec.rules.exit.reduce_fraction_column)
    if spec.rules.exit.add_fraction_column is not None:
        columns.add(spec.rules.exit.add_fraction_column)
    if spec.rules.exit.rebalance_target_fraction_column is not None:
        columns.add(spec.rules.exit.rebalance_target_fraction_column)
    if spec.rules.exit.rebalance_min_delta_fraction_column is not None:
        columns.add(spec.rules.exit.rebalance_min_delta_fraction_column)
    if spec.rules.sizing.position_weight_column is not None:
        columns.add(spec.rules.sizing.position_weight_column)
    if spec.rules.sizing.notional_usd_column is not None:
        columns.add(spec.rules.sizing.notional_usd_column)
    if spec.rules.sizing.volatility_column is not None:
        columns.add(spec.rules.sizing.volatility_column)
    if spec.rules.bracket.time_stop_minutes_column is not None:
        add_column(spec.rules.bracket.time_stop_minutes_column)
    if spec.rules.bracket.break_even_after_bps_column is not None:
        add_column(spec.rules.bracket.break_even_after_bps_column)
    if (
        spec.rules.execution.max_latency_ms is not None
        or spec.rules.execution.max_latency_ms_column is not None
    ) and spec.rules.execution.latency_column is not None:
        add_column(spec.rules.execution.latency_column)
    if spec.rules.execution.slippage_bps_column is not None:
        add_column(spec.rules.execution.slippage_bps_column)
    if spec.rules.execution.max_fill_fraction_column is not None:
        add_column(spec.rules.execution.max_fill_fraction_column)
    if spec.rules.execution.min_fill_fraction_column is not None:
        add_column(spec.rules.execution.min_fill_fraction_column)
    if spec.rules.execution.max_spread_bps_column is not None:
        add_column(spec.rules.execution.max_spread_bps_column)
    if spec.rules.execution.min_depth_usd_column is not None:
        add_column(spec.rules.execution.min_depth_usd_column)
    if spec.rules.execution.max_latency_ms_column is not None:
        add_column(spec.rules.execution.max_latency_ms_column)
    if (
        spec.rules.execution.min_queue_position_score is not None
        or spec.rules.execution.min_queue_position_score_column is not None
    ) and spec.rules.execution.queue_position_score_column is not None:
        add_column(spec.rules.execution.queue_position_score_column)
    if spec.rules.execution.min_queue_position_score_column is not None:
        add_column(spec.rules.execution.min_queue_position_score_column)
    if (
        spec.rules.execution.min_borrow_availability_ratio is not None
        or spec.rules.execution.min_borrow_availability_ratio_column is not None
    ) and spec.rules.execution.borrow_availability_column is not None:
        add_column(spec.rules.execution.borrow_availability_column)
    if spec.rules.execution.min_borrow_availability_ratio_column is not None:
        add_column(spec.rules.execution.min_borrow_availability_ratio_column)
    if (
        spec.rules.execution.max_borrow_cost_bps is not None
        or spec.rules.execution.max_borrow_cost_bps_column is not None
    ) and spec.rules.execution.borrow_cost_column is not None:
        add_column(spec.rules.execution.borrow_cost_column)
    if spec.rules.execution.max_borrow_cost_bps_column is not None:
        add_column(spec.rules.execution.max_borrow_cost_bps_column)
    if (
        spec.rules.execution.max_tax_drag_bps is not None
        or spec.rules.execution.max_tax_drag_bps_column is not None
    ) and spec.rules.execution.tax_drag_column is not None:
        add_column(spec.rules.execution.tax_drag_column)
    if spec.rules.execution.max_tax_drag_bps_column is not None:
        add_column(spec.rules.execution.max_tax_drag_bps_column)
    if (
        spec.rules.execution.max_turnover_pressure is not None
        or spec.rules.execution.max_turnover_pressure_column is not None
    ) and spec.rules.execution.turnover_pressure_column is not None:
        add_column(spec.rules.execution.turnover_pressure_column)
    if spec.rules.execution.max_turnover_pressure_column is not None:
        add_column(spec.rules.execution.max_turnover_pressure_column)
    if (
        spec.rules.execution.max_capacity_usage_ratio is not None
        or spec.rules.execution.max_capacity_usage_ratio_column is not None
    ) and spec.rules.execution.capacity_usage_column is not None:
        add_column(spec.rules.execution.capacity_usage_column)
    if spec.rules.execution.max_capacity_usage_ratio_column is not None:
        add_column(spec.rules.execution.max_capacity_usage_ratio_column)
    if (
        spec.rules.execution.max_correlation_crowding_score is not None
        or spec.rules.execution.max_correlation_crowding_score_column is not None
    ) and spec.rules.execution.correlation_crowding_column is not None:
        add_column(spec.rules.execution.correlation_crowding_column)
    if spec.rules.execution.max_correlation_crowding_score_column is not None:
        add_column(spec.rules.execution.max_correlation_crowding_score_column)
    if (
        spec.rules.execution.min_fee_edge_bps is not None
        or spec.rules.execution.min_fee_edge_bps_column is not None
    ) and spec.rules.execution.fee_edge_column is not None:
        add_column(spec.rules.execution.fee_edge_column)
    if spec.rules.execution.min_fee_edge_bps_column is not None:
        add_column(spec.rules.execution.min_fee_edge_bps_column)
    if spec.rules.portfolio.allocation_volatility_column is not None:
        columns.add(spec.rules.portfolio.allocation_volatility_column)
    if spec.rules.portfolio.allocation_beta_column is not None:
        columns.add(spec.rules.portfolio.allocation_beta_column)
    if spec.rules.portfolio.target_total_position_weight_column is not None:
        columns.add(spec.rules.portfolio.target_total_position_weight_column)
    if spec.rules.portfolio.max_total_position_weight_column is not None:
        columns.add(spec.rules.portfolio.max_total_position_weight_column)
    if spec.rules.portfolio.max_long_position_weight_column is not None:
        columns.add(spec.rules.portfolio.max_long_position_weight_column)
    if spec.rules.portfolio.max_short_position_weight_column is not None:
        columns.add(spec.rules.portfolio.max_short_position_weight_column)
    if spec.rules.portfolio.max_abs_net_position_weight_column is not None:
        columns.add(spec.rules.portfolio.max_abs_net_position_weight_column)
    if spec.rules.portfolio.max_symbol_position_weight_column is not None:
        columns.add(spec.rules.portfolio.max_symbol_position_weight_column)
    if spec.rules.portfolio.max_group_position_weight_column is not None:
        columns.add(spec.rules.portfolio.max_group_position_weight_column)
    if spec.rules.portfolio.max_group_abs_net_position_weight_column is not None:
        columns.add(spec.rules.portfolio.max_group_abs_net_position_weight_column)
    if spec.rules.portfolio.group_column is not None:
        columns.add(spec.rules.portfolio.group_column)
    if spec.rules.portfolio.turnover_weight_column is not None:
        columns.add(spec.rules.portfolio.turnover_weight_column)
    if spec.rules.cross_sectional.group_column is not None:
        columns.add(spec.rules.cross_sectional.group_column)
    if spec.rules.risk_throttle.max_drawdown_column is not None:
        columns.add(spec.rules.risk_throttle.max_drawdown_column)
    if spec.rules.risk_throttle.max_drawdown_floor_column is not None:
        columns.add(spec.rules.risk_throttle.max_drawdown_floor_column)
    if spec.rules.risk_throttle.daily_loss_column is not None:
        columns.add(spec.rules.risk_throttle.daily_loss_column)
    if spec.rules.risk_throttle.daily_loss_floor_column is not None:
        columns.add(spec.rules.risk_throttle.daily_loss_floor_column)
    if spec.rules.risk_throttle.loss_streak_column is not None:
        columns.add(spec.rules.risk_throttle.loss_streak_column)
    if spec.rules.risk_throttle.max_loss_streak_column is not None:
        columns.add(spec.rules.risk_throttle.max_loss_streak_column)
    data_guard = spec.rules.data_guard
    if (
        data_guard.max_feature_age_minutes is not None
        or data_guard.max_feature_age_minutes_column is not None
    ) and data_guard.feature_age_column is not None:
        columns.add(data_guard.feature_age_column)
    if data_guard.max_feature_age_minutes_column is not None:
        columns.add(data_guard.max_feature_age_minutes_column)
    if (
        data_guard.min_source_confidence is not None
        or data_guard.min_source_confidence_column is not None
    ) and data_guard.source_confidence_column is not None:
        columns.add(data_guard.source_confidence_column)
    if data_guard.min_source_confidence_column is not None:
        columns.add(data_guard.min_source_confidence_column)
    if (
        data_guard.min_venue_quality_score is not None
        or data_guard.min_venue_quality_score_column is not None
    ) and data_guard.venue_quality_score_column is not None:
        columns.add(data_guard.venue_quality_score_column)
    if data_guard.min_venue_quality_score_column is not None:
        columns.add(data_guard.min_venue_quality_score_column)
    if (
        data_guard.max_staleness_bps is not None or data_guard.max_staleness_bps_column is not None
    ) and data_guard.staleness_bps_column is not None:
        columns.add(data_guard.staleness_bps_column)
    if data_guard.max_staleness_bps_column is not None:
        columns.add(data_guard.max_staleness_bps_column)
    if (
        data_guard.max_regime_transition_score is not None
        or data_guard.max_regime_transition_score_column is not None
    ) and data_guard.regime_transition_score_column is not None:
        columns.add(data_guard.regime_transition_score_column)
    if data_guard.max_regime_transition_score_column is not None:
        columns.add(data_guard.max_regime_transition_score_column)
    for event_window in spec.rules.event_windows:
        columns.add(event_window.event_ts_column)
    for leg in spec.rules.multi_leg.legs:
        if leg.position_weight_column is not None:
            columns.add(leg.position_weight_column)
        if leg.notional_usd_column is not None:
            columns.add(leg.notional_usd_column)
        for column_name in (
            leg.stop_loss_bps_column,
            leg.min_stop_loss_bps_column,
            leg.max_stop_loss_bps_column,
            leg.take_profit_bps_column,
            leg.min_take_profit_bps_column,
            leg.max_take_profit_bps_column,
            leg.trailing_stop_bps_column,
            leg.trailing_stop_activation_bps_column,
            leg.partial_take_profit_bps_column,
            leg.partial_exit_fraction_column,
            leg.min_reward_risk_ratio_column,
            leg.entry_type_column,
            leg.limit_offset_bps_column,
            leg.stop_offset_bps_column,
            leg.timeout_minutes_column,
            leg.time_in_force_column,
            leg.post_only_column,
            leg.reduce_only_column,
            leg.slippage_bps_column,
            leg.max_fill_fraction_column,
            leg.min_fill_fraction_column,
            leg.max_spread_bps_column,
            leg.min_depth_usd_column,
            leg.max_latency_ms_column,
            leg.min_queue_position_score_column,
            leg.min_borrow_availability_ratio_column,
            leg.max_borrow_cost_bps_column,
            leg.max_tax_drag_bps_column,
            leg.max_turnover_pressure_column,
            leg.max_capacity_usage_ratio_column,
            leg.max_correlation_crowding_score_column,
            leg.min_fee_edge_bps_column,
        ):
            if column_name is not None:
                columns.add(column_name)
        if (
            leg.max_latency_ms is not None or leg.max_latency_ms_column is not None
        ) and leg.latency_column is not None:
            columns.add(leg.latency_column)
        if (
            leg.min_queue_position_score is not None
            or leg.min_queue_position_score_column is not None
        ) and leg.queue_position_score_column is not None:
            columns.add(leg.queue_position_score_column)
        if (
            leg.min_borrow_availability_ratio is not None
            or leg.min_borrow_availability_ratio_column is not None
        ) and leg.borrow_availability_column is not None:
            columns.add(leg.borrow_availability_column)
        if (
            leg.max_borrow_cost_bps is not None or leg.max_borrow_cost_bps_column is not None
        ) and leg.borrow_cost_column is not None:
            columns.add(leg.borrow_cost_column)
        if (
            leg.max_tax_drag_bps is not None or leg.max_tax_drag_bps_column is not None
        ) and leg.tax_drag_column is not None:
            columns.add(leg.tax_drag_column)
        if (
            leg.max_turnover_pressure is not None or leg.max_turnover_pressure_column is not None
        ) and leg.turnover_pressure_column is not None:
            columns.add(leg.turnover_pressure_column)
        if (
            leg.max_capacity_usage_ratio is not None
            or leg.max_capacity_usage_ratio_column is not None
        ) and leg.capacity_usage_column is not None:
            columns.add(leg.capacity_usage_column)
        if (
            leg.max_correlation_crowding_score is not None
            or leg.max_correlation_crowding_score_column is not None
        ) and leg.correlation_crowding_column is not None:
            columns.add(leg.correlation_crowding_column)
        if (
            leg.min_fee_edge_bps is not None or leg.min_fee_edge_bps_column is not None
        ) and leg.fee_edge_column is not None:
            columns.add(leg.fee_edge_column)
    return columns


def _all_conditions(spec: StrategyAuthoringSpec) -> list[Condition]:
    groups = [
        spec.rules.entry,
        spec.rules.long_entry,
        spec.rules.short_entry,
        spec.rules.hold,
        spec.rules.close,
        spec.rules.reduce,
        spec.rules.add,
        spec.rules.rebalance,
        *(regime.when for regime in spec.rules.regime_overrides),
    ]
    conditions: list[Condition] = []
    for group in groups:
        if group is not None:
            conditions.extend([*group.all, *group.any, *group.none])
    return conditions


def validate_authoring_inputs(spec: StrategyAuthoringSpec, *, data_dir: Path) -> list[str]:
    errors: list[str] = []
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    if not feature_path.exists():
        errors.append(f"feature_panel_path not found: {feature_path}")
        return errors
    try:
        feature = pl.read_parquet(feature_path, n_rows=1)
    except Exception as exc:  # pragma: no cover - polars gives version-specific exceptions
        errors.append(f"feature_panel_path is not readable parquet: {exc}")
        return errors
    available_columns = set(feature.columns)
    for panel in spec.data.confirmation_panels:
        panel_path = _resolve_path(panel.path, data_dir)
        if not panel_path.exists():
            errors.append(f"confirmation panel not found: {panel_path}")
            continue
        try:
            panel_frame = pl.read_parquet(panel_path, n_rows=1)
        except Exception as exc:  # pragma: no cover - polars gives version-specific exceptions
            errors.append(f"confirmation panel is not readable parquet: {panel_path}: {exc}")
            continue
        required_panel_columns = {"ts", "canonical_symbol"}
        missing_panel_columns = sorted(required_panel_columns.difference(panel_frame.columns))
        if missing_panel_columns:
            errors.append(
                f"confirmation panel missing columns: {panel_path}: {missing_panel_columns}"
            )
            continue
        available_columns.update(_prefixed_confirmation_columns(panel, set(panel_frame.columns)))
    missing = sorted(_required_columns(spec).difference(available_columns))
    if missing:
        errors.append(f"feature panel missing columns: {missing}")
    generated: set[str] = set()
    base_columns = available_columns
    for derived in spec.rules.derived_features:
        available = base_columns.union(generated)
        missing_inputs = sorted(set(derived.columns).difference(available))
        if missing_inputs:
            errors.append(f"derived feature {derived.name} missing input columns: {missing_inputs}")
        generated.add(derived.name)
    binding_symbols = {binding.real_market_symbol for binding in spec.experiment.symbol_bindings}
    if spec.rules.multi_leg.enabled:
        symbols = {str(spec.rules.multi_leg.anchor_real_market_symbol)}
        leg_symbols = {leg.real_market_symbol for leg in spec.rules.multi_leg.legs}
        missing_bindings = sorted(leg_symbols.union(symbols).difference(binding_symbols))
        if missing_bindings:
            errors.append(f"multi_leg symbols missing symbol_bindings: {missing_bindings}")
    else:
        symbols = binding_symbols
    if "canonical_symbol" in feature.columns:
        full = pl.read_parquet(feature_path, columns=["canonical_symbol"])
        observed = {str(value).upper() for value in full.get_column("canonical_symbol").to_list()}
        missing_symbols = sorted(symbols.difference(observed))
        if missing_symbols:
            errors.append(f"feature panel missing real_market_symbol rows: {missing_symbols}")
    return errors
