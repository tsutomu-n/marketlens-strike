from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.paper_preview_execution_fields import (
    _paper_preview_execution_fields,
)


def test_paper_preview_execution_fields_use_selected_row_values() -> None:
    fields = _paper_preview_execution_fields(
        row={
            "slippage_bps": 1.5,
            "max_fill_fraction": 0.8,
            "min_fill_fraction": 0.2,
            "max_spread_bps": 4.0,
            "min_depth_usd": 10_000.0,
            "depth_column": "depth_10bps",
            "depth_participation_rate": 0.25,
            "max_latency_ms": 50.0,
            "latency_ms": 12.0,
            "min_queue_position_score": 0.4,
            "queue_position_score": 0.7,
            "min_borrow_availability_ratio": 0.9,
            "borrow_availability_ratio": 0.95,
            "max_borrow_cost_bps": 7.0,
            "borrow_cost_bps": 2.0,
            "max_tax_drag_bps": 3.0,
            "tax_drag_bps": 1.5,
            "max_turnover_pressure": 0.6,
            "turnover_pressure": 0.3,
            "max_capacity_usage_ratio": 0.75,
            "capacity_usage_ratio": 0.5,
            "max_correlation_crowding_score": 0.65,
            "correlation_crowding_score": 0.45,
            "min_fee_edge_bps": 1.0,
            "fee_edge_bps": -0.5,
        },
        selected=True,
    )

    assert fields == {
        "slippage_bps": 1.5,
        "max_fill_fraction": 0.8,
        "min_fill_fraction": 0.2,
        "max_spread_bps": 4.0,
        "min_depth_usd": 10_000.0,
        "depth_column": "depth_10bps",
        "depth_participation_rate": 0.25,
        "max_latency_ms": 50.0,
        "latency_ms": 12.0,
        "min_queue_position_score": 0.4,
        "queue_position_score": 0.7,
        "min_borrow_availability_ratio": 0.9,
        "borrow_availability_ratio": 0.95,
        "max_borrow_cost_bps": 7.0,
        "borrow_cost_bps": 2.0,
        "max_tax_drag_bps": 3.0,
        "tax_drag_bps": 1.5,
        "max_turnover_pressure": 0.6,
        "turnover_pressure": 0.3,
        "max_capacity_usage_ratio": 0.75,
        "capacity_usage_ratio": 0.5,
        "max_correlation_crowding_score": 0.65,
        "correlation_crowding_score": 0.45,
        "min_fee_edge_bps": 1.0,
        "fee_edge_bps": -0.5,
    }


def test_paper_preview_execution_fields_preserve_unselected_defaults() -> None:
    fields = _paper_preview_execution_fields(
        row={
            "slippage_bps": 1.5,
            "max_fill_fraction": 0.8,
            "depth_participation_rate": 0.25,
            "max_borrow_cost_bps": 7.0,
        },
        selected=False,
    )

    assert fields == {
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "max_capacity_usage_ratio": None,
        "capacity_usage_ratio": None,
        "max_correlation_crowding_score": None,
        "correlation_crowding_score": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
    }
