from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.multi_leg import MultiLegEntry
from sis.research.strategy_lab.authoring.multi_leg_required_columns import (
    _multi_leg_required_columns,
)


def test_multi_leg_required_columns_collect_direct_leg_column_fields() -> None:
    columns = _multi_leg_required_columns(
        [
            MultiLegEntry(
                real_market_symbol="BBB",
                side="opposite",
                position_weight_column="hedge_ratio",
                notional_usd_column="hedge_notional_usd",
                stop_loss_bps_column="hedge_stop_loss_bps",
                entry_type_column="hedge_entry_type",
                slippage_bps_column="hedge_slippage_bps",
                min_fee_edge_bps_column="hedge_min_fee_edge_bps",
            )
        ]
    )

    assert {
        "hedge_ratio",
        "hedge_notional_usd",
        "hedge_stop_loss_bps",
        "hedge_entry_type",
        "hedge_slippage_bps",
        "hedge_min_fee_edge_bps",
    }.issubset(columns)


def test_multi_leg_required_columns_collect_conditional_observed_columns() -> None:
    columns = _multi_leg_required_columns(
        [
            MultiLegEntry(
                real_market_symbol="BBB",
                side="opposite",
                max_latency_ms=50.0,
                latency_column="hedge_latency_ms",
                min_queue_position_score_column="hedge_queue_required",
                queue_position_score_column="hedge_queue_score",
                min_borrow_availability_ratio=0.5,
                borrow_availability_column="hedge_borrow_available",
                max_borrow_cost_bps_column="hedge_borrow_cost_cap",
                borrow_cost_column="hedge_borrow_cost_bps",
                max_tax_drag_bps=7.0,
                tax_drag_column="hedge_tax_drag_bps",
                max_turnover_pressure_column="hedge_turnover_cap",
                turnover_pressure_column="hedge_turnover_pressure",
                max_capacity_usage_ratio=0.8,
                capacity_usage_column="hedge_capacity_usage",
                max_correlation_crowding_score_column="hedge_crowding_cap",
                correlation_crowding_column="hedge_crowding_score",
                min_fee_edge_bps=2.0,
                fee_edge_column="hedge_fee_edge_bps",
            )
        ]
    )

    assert {
        "hedge_latency_ms",
        "hedge_queue_required",
        "hedge_queue_score",
        "hedge_borrow_available",
        "hedge_borrow_cost_cap",
        "hedge_borrow_cost_bps",
        "hedge_tax_drag_bps",
        "hedge_turnover_cap",
        "hedge_turnover_pressure",
        "hedge_capacity_usage",
        "hedge_crowding_cap",
        "hedge_crowding_score",
        "hedge_fee_edge_bps",
    }.issubset(columns)


def test_multi_leg_required_columns_skip_unconfigured_observed_columns() -> None:
    columns = _multi_leg_required_columns(
        [
            MultiLegEntry(
                real_market_symbol="BBB",
                side="opposite",
                latency_column="hedge_latency_ms",
                queue_position_score_column="hedge_queue_score",
                borrow_availability_column="hedge_borrow_available",
                borrow_cost_column="hedge_borrow_cost_bps",
                tax_drag_column="hedge_tax_drag_bps",
                turnover_pressure_column="hedge_turnover_pressure",
                capacity_usage_column="hedge_capacity_usage",
                correlation_crowding_column="hedge_crowding_score",
                fee_edge_column="hedge_fee_edge_bps",
            )
        ]
    )

    assert columns == set()
