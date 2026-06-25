from __future__ import annotations

from collections.abc import Iterable

from sis.research.strategy_lab.authoring.contracts.multi_leg import MultiLegEntry


def _multi_leg_required_columns(legs: Iterable[MultiLegEntry]) -> set[str]:
    columns: set[str] = set()
    for leg in legs:
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
