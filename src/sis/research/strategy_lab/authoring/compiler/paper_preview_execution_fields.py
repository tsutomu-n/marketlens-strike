from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import _float_or_default


def _paper_preview_execution_fields(*, row: dict[str, Any], selected: bool) -> dict[str, Any]:
    use_row = selected and bool(row)
    return {
        "slippage_bps": _float_or_default(row.get("slippage_bps") if use_row else None, 0.0),
        "max_fill_fraction": _float_or_default(
            row.get("max_fill_fraction") if use_row else None,
            0.0,
        ),
        "min_fill_fraction": row.get("min_fill_fraction") if use_row else None,
        "max_spread_bps": row.get("max_spread_bps") if use_row else None,
        "min_depth_usd": row.get("min_depth_usd") if use_row else None,
        "depth_column": row.get("depth_column") if use_row else None,
        "depth_participation_rate": _float_or_default(
            row.get("depth_participation_rate") if use_row else None,
            0.0,
        ),
        "max_latency_ms": row.get("max_latency_ms") if use_row else None,
        "latency_ms": row.get("latency_ms") if use_row else None,
        "min_queue_position_score": row.get("min_queue_position_score") if use_row else None,
        "queue_position_score": row.get("queue_position_score") if use_row else None,
        "min_borrow_availability_ratio": row.get("min_borrow_availability_ratio")
        if use_row
        else None,
        "borrow_availability_ratio": row.get("borrow_availability_ratio") if use_row else None,
        "max_borrow_cost_bps": row.get("max_borrow_cost_bps") if use_row else None,
        "borrow_cost_bps": row.get("borrow_cost_bps") if use_row else None,
        "max_tax_drag_bps": row.get("max_tax_drag_bps") if use_row else None,
        "tax_drag_bps": row.get("tax_drag_bps") if use_row else None,
        "max_turnover_pressure": row.get("max_turnover_pressure") if use_row else None,
        "turnover_pressure": row.get("turnover_pressure") if use_row else None,
        "max_capacity_usage_ratio": row.get("max_capacity_usage_ratio") if use_row else None,
        "capacity_usage_ratio": row.get("capacity_usage_ratio") if use_row else None,
        "max_correlation_crowding_score": row.get("max_correlation_crowding_score")
        if use_row
        else None,
        "correlation_crowding_score": row.get("correlation_crowding_score") if use_row else None,
        "min_fee_edge_bps": row.get("min_fee_edge_bps") if use_row else None,
        "fee_edge_bps": row.get("fee_edge_bps") if use_row else None,
    }
