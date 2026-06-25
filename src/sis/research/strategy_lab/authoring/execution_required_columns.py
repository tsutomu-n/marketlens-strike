from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import ExecutionRules


def _execution_required_columns(execution: ExecutionRules) -> set[str]:
    columns: set[str] = set()
    if (
        execution.max_latency_ms is not None or execution.max_latency_ms_column is not None
    ) and execution.latency_column is not None:
        columns.add(execution.latency_column)
    for column_name in (
        execution.slippage_bps_column,
        execution.max_fill_fraction_column,
        execution.min_fill_fraction_column,
        execution.max_spread_bps_column,
        execution.min_depth_usd_column,
        execution.max_latency_ms_column,
        execution.min_queue_position_score_column,
        execution.min_borrow_availability_ratio_column,
        execution.max_borrow_cost_bps_column,
        execution.max_tax_drag_bps_column,
        execution.max_turnover_pressure_column,
        execution.max_capacity_usage_ratio_column,
        execution.max_correlation_crowding_score_column,
        execution.min_fee_edge_bps_column,
    ):
        if column_name is not None:
            columns.add(column_name)
    if (
        execution.min_queue_position_score is not None
        or execution.min_queue_position_score_column is not None
    ) and execution.queue_position_score_column is not None:
        columns.add(execution.queue_position_score_column)
    if (
        execution.min_borrow_availability_ratio is not None
        or execution.min_borrow_availability_ratio_column is not None
    ) and execution.borrow_availability_column is not None:
        columns.add(execution.borrow_availability_column)
    if (
        execution.max_borrow_cost_bps is not None
        or execution.max_borrow_cost_bps_column is not None
    ) and execution.borrow_cost_column is not None:
        columns.add(execution.borrow_cost_column)
    if (
        execution.max_tax_drag_bps is not None or execution.max_tax_drag_bps_column is not None
    ) and execution.tax_drag_column is not None:
        columns.add(execution.tax_drag_column)
    if (
        execution.max_turnover_pressure is not None
        or execution.max_turnover_pressure_column is not None
    ) and execution.turnover_pressure_column is not None:
        columns.add(execution.turnover_pressure_column)
    if (
        execution.max_capacity_usage_ratio is not None
        or execution.max_capacity_usage_ratio_column is not None
    ) and execution.capacity_usage_column is not None:
        columns.add(execution.capacity_usage_column)
    if (
        execution.max_correlation_crowding_score is not None
        or execution.max_correlation_crowding_score_column is not None
    ) and execution.correlation_crowding_column is not None:
        columns.add(execution.correlation_crowding_column)
    if (
        execution.min_fee_edge_bps is not None or execution.min_fee_edge_bps_column is not None
    ) and execution.fee_edge_column is not None:
        columns.add(execution.fee_edge_column)
    return columns
