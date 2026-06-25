from __future__ import annotations

from typing import Any


def _research_signal_execution_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "slippage_bps": row.get("slippage_bps") or 0.0,
        "max_fill_fraction": row.get("max_fill_fraction") or 1.0,
        "min_fill_fraction": row.get("min_fill_fraction"),
        "max_spread_bps": row.get("max_spread_bps"),
        "min_depth_usd": row.get("min_depth_usd"),
        "depth_column": row.get("depth_column"),
        "depth_participation_rate": row.get("depth_participation_rate") or 1.0,
        "max_latency_ms": row.get("max_latency_ms"),
        "latency_ms": row.get("latency_ms"),
        "min_queue_position_score": row.get("min_queue_position_score"),
        "queue_position_score": row.get("queue_position_score"),
        "min_borrow_availability_ratio": row.get("min_borrow_availability_ratio"),
        "borrow_availability_ratio": row.get("borrow_availability_ratio"),
        "max_borrow_cost_bps": row.get("max_borrow_cost_bps"),
        "borrow_cost_bps": row.get("borrow_cost_bps"),
        "max_tax_drag_bps": row.get("max_tax_drag_bps"),
        "tax_drag_bps": row.get("tax_drag_bps"),
        "max_turnover_pressure": row.get("max_turnover_pressure"),
        "turnover_pressure": row.get("turnover_pressure"),
        "max_capacity_usage_ratio": row.get("max_capacity_usage_ratio"),
        "capacity_usage_ratio": row.get("capacity_usage_ratio"),
        "max_correlation_crowding_score": row.get("max_correlation_crowding_score"),
        "correlation_crowding_score": row.get("correlation_crowding_score"),
        "min_fee_edge_bps": row.get("min_fee_edge_bps"),
        "fee_edge_bps": row.get("fee_edge_bps"),
    }
