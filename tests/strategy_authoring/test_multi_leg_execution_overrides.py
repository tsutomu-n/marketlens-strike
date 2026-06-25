from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.multi_leg_execution_overrides import (
    _multi_leg_execution_overrides,
)
from sis.research.strategy_lab.authoring.contracts.multi_leg import MultiLegEntry


def test_multi_leg_execution_overrides_resolve_thresholds_and_observed_columns() -> None:
    row = {
        "slippage": 22,
        "min_fill": "0.3",
        "spread_cap": 12,
        "borrow_cost_cap": 8,
        "crowding_cap": 0.65,
        "fee_edge_req": -1.2,
    }
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
        slippage_bps_column="slippage",
        max_fill_fraction=0.4,
        min_fill_fraction_column="min_fill",
        max_spread_bps_column="spread_cap",
        min_depth_usd=1000,
        max_latency_ms=50,
        depth_participation_rate=0.2,
        min_queue_position_score=0.7,
        min_borrow_availability_ratio=0.8,
        max_borrow_cost_bps_column="borrow_cost_cap",
        max_tax_drag_bps=7,
        max_turnover_pressure=0.35,
        max_capacity_usage_ratio=0.55,
        max_correlation_crowding_score_column="crowding_cap",
        min_fee_edge_bps_column="fee_edge_req",
        depth_column="depth_usd",
        latency_column="latency_ms",
        queue_position_score_column="queue_score",
        borrow_availability_column="borrow_available",
        borrow_cost_column="borrow_cost_bps",
        tax_drag_column="tax_drag_bps",
        turnover_pressure_column="turnover_pressure",
        capacity_usage_column="capacity_usage",
        correlation_crowding_column="correlation_crowding",
        fee_edge_column="fee_edge_bps",
    )

    assert _multi_leg_execution_overrides(row=row, leg=leg) == {
        "slippage_bps": 22.0,
        "max_spread_bps": 12.0,
        "min_depth_usd": 1000.0,
        "max_latency_ms": 50.0,
        "max_borrow_cost_bps": 8.0,
        "max_tax_drag_bps": 7.0,
        "max_turnover_pressure": 0.35,
        "max_capacity_usage_ratio": 0.55,
        "max_correlation_crowding_score": 0.65,
        "max_fill_fraction": 0.4,
        "min_fill_fraction": 0.3,
        "depth_participation_rate": 0.2,
        "min_queue_position_score": 0.7,
        "min_borrow_availability_ratio": 0.8,
        "min_fee_edge_bps": -1.2,
        "depth_column": "depth_usd",
        "latency_column": "latency_ms",
        "queue_position_score_column": "queue_score",
        "borrow_availability_column": "borrow_available",
        "borrow_cost_column": "borrow_cost_bps",
        "tax_drag_column": "tax_drag_bps",
        "turnover_pressure_column": "turnover_pressure",
        "capacity_usage_column": "capacity_usage",
        "correlation_crowding_column": "correlation_crowding",
        "fee_edge_column": "fee_edge_bps",
    }
