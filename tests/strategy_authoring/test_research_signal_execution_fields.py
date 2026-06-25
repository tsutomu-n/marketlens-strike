from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.research_signal_execution_fields import (
    _research_signal_execution_fields,
)


def test_research_signal_execution_fields_apply_defaults() -> None:
    fields = _research_signal_execution_fields({})

    assert fields["slippage_bps"] == 0.0
    assert fields["max_fill_fraction"] == 1.0
    assert fields["depth_participation_rate"] == 1.0
    assert fields["min_fill_fraction"] is None
    assert fields["max_spread_bps"] is None
    assert fields["min_depth_usd"] is None
    assert fields["latency_ms"] is None
    assert fields["queue_position_score"] is None


def test_research_signal_execution_fields_pass_through_microstructure_values() -> None:
    fields = _research_signal_execution_fields(
        {
            "slippage_bps": 4.5,
            "max_fill_fraction": 0.8,
            "min_fill_fraction": 0.2,
            "max_spread_bps": 12.0,
            "min_depth_usd": 25_000.0,
            "depth_column": "depth_usd",
            "depth_participation_rate": 0.25,
            "max_latency_ms": 50.0,
            "latency_ms": 12.0,
            "min_queue_position_score": 0.4,
            "queue_position_score": 0.7,
            "min_borrow_availability_ratio": 0.9,
            "borrow_availability_ratio": 0.95,
            "max_borrow_cost_bps": 8.0,
            "borrow_cost_bps": 3.0,
            "max_tax_drag_bps": 5.0,
            "tax_drag_bps": 2.0,
            "max_turnover_pressure": 0.3,
            "turnover_pressure": 0.2,
            "max_capacity_usage_ratio": 0.6,
            "capacity_usage_ratio": 0.45,
            "max_correlation_crowding_score": 0.7,
            "correlation_crowding_score": 0.5,
            "min_fee_edge_bps": -1.0,
            "fee_edge_bps": 1.5,
        }
    )

    assert fields == {
        "slippage_bps": 4.5,
        "max_fill_fraction": 0.8,
        "min_fill_fraction": 0.2,
        "max_spread_bps": 12.0,
        "min_depth_usd": 25_000.0,
        "depth_column": "depth_usd",
        "depth_participation_rate": 0.25,
        "max_latency_ms": 50.0,
        "latency_ms": 12.0,
        "min_queue_position_score": 0.4,
        "queue_position_score": 0.7,
        "min_borrow_availability_ratio": 0.9,
        "borrow_availability_ratio": 0.95,
        "max_borrow_cost_bps": 8.0,
        "borrow_cost_bps": 3.0,
        "max_tax_drag_bps": 5.0,
        "tax_drag_bps": 2.0,
        "max_turnover_pressure": 0.3,
        "turnover_pressure": 0.2,
        "max_capacity_usage_ratio": 0.6,
        "capacity_usage_ratio": 0.45,
        "max_correlation_crowding_score": 0.7,
        "correlation_crowding_score": 0.5,
        "min_fee_edge_bps": -1.0,
        "fee_edge_bps": 1.5,
    }
