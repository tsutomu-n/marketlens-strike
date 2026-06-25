from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import ExecutionRules
from sis.research.strategy_lab.authoring.execution_required_columns import (
    _execution_required_columns,
)


def test_execution_required_columns_collect_direct_override_columns() -> None:
    columns = _execution_required_columns(
        ExecutionRules(
            slippage_bps_column="row_slippage",
            max_fill_fraction_column="row_max_fill",
            min_fill_fraction_column="row_min_fill",
            max_spread_bps_column="row_max_spread",
            min_depth_usd_column="row_min_depth",
            max_latency_ms_column="row_max_latency",
            min_queue_position_score_column="row_min_queue",
            min_borrow_availability_ratio_column="row_min_borrow",
            max_borrow_cost_bps_column="row_max_borrow_cost",
            max_tax_drag_bps_column="row_max_tax_drag",
            max_turnover_pressure_column="row_max_turnover",
            max_capacity_usage_ratio_column="row_max_capacity",
            max_correlation_crowding_score_column="row_max_crowding",
            min_fee_edge_bps_column="row_min_fee_edge",
        )
    )

    assert {
        "row_slippage",
        "row_max_fill",
        "row_min_fill",
        "row_max_spread",
        "row_min_depth",
        "row_max_latency",
        "row_min_queue",
        "row_min_borrow",
        "row_max_borrow_cost",
        "row_max_tax_drag",
        "row_max_turnover",
        "row_max_capacity",
        "row_max_crowding",
        "row_min_fee_edge",
    }.issubset(columns)


def test_execution_required_columns_collect_conditional_observed_columns() -> None:
    columns = _execution_required_columns(
        ExecutionRules(
            max_latency_ms=100.0,
            latency_column="observed_latency",
            min_queue_position_score_column="row_min_queue",
            queue_position_score_column="observed_queue",
            min_borrow_availability_ratio=0.5,
            borrow_availability_column="observed_borrow",
            max_borrow_cost_bps_column="row_max_borrow_cost",
            borrow_cost_column="observed_borrow_cost",
            max_tax_drag_bps=10.0,
            tax_drag_column="observed_tax_drag",
            max_turnover_pressure_column="row_max_turnover",
            turnover_pressure_column="observed_turnover",
            max_capacity_usage_ratio=0.8,
            capacity_usage_column="observed_capacity",
            max_correlation_crowding_score_column="row_max_crowding",
            correlation_crowding_column="observed_crowding",
            min_fee_edge_bps=1.0,
            fee_edge_column="observed_fee_edge",
        )
    )

    assert {
        "observed_latency",
        "row_min_queue",
        "observed_queue",
        "observed_borrow",
        "row_max_borrow_cost",
        "observed_borrow_cost",
        "observed_tax_drag",
        "row_max_turnover",
        "observed_turnover",
        "observed_capacity",
        "row_max_crowding",
        "observed_crowding",
        "observed_fee_edge",
    }.issubset(columns)


def test_execution_required_columns_skip_unconfigured_observed_columns() -> None:
    columns = _execution_required_columns(
        ExecutionRules(
            latency_column="observed_latency",
            queue_position_score_column="observed_queue",
            borrow_availability_column="observed_borrow",
            borrow_cost_column="observed_borrow_cost",
            tax_drag_column="observed_tax_drag",
            turnover_pressure_column="observed_turnover",
            capacity_usage_column="observed_capacity",
            correlation_crowding_column="observed_crowding",
            fee_edge_column="observed_fee_edge",
        )
    )

    assert columns == set()
