from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_values import (
    _non_negative_value,
    _sizing_value,
    _unit_interval_value,
)


def _multi_leg_execution_overrides(*, row: dict[str, Any], leg: Any) -> dict[str, Any]:
    execution_overrides: dict[str, Any] = {}
    for field_name in (
        "slippage_bps",
        "max_spread_bps",
        "min_depth_usd",
        "max_latency_ms",
        "max_borrow_cost_bps",
        "max_tax_drag_bps",
        "max_turnover_pressure",
        "max_capacity_usage_ratio",
        "max_correlation_crowding_score",
    ):
        value = _non_negative_value(
            row,
            fixed=getattr(leg, field_name),
            column=getattr(leg, f"{field_name}_column"),
            field_name=f"rules.multi_leg.legs[].{field_name}",
        )
        if value is not None:
            execution_overrides[field_name] = value
    for field_name in (
        "max_fill_fraction",
        "min_fill_fraction",
        "depth_participation_rate",
        "min_queue_position_score",
        "min_borrow_availability_ratio",
    ):
        value = _unit_interval_value(
            row,
            fixed=getattr(leg, field_name),
            column=getattr(leg, f"{field_name}_column", None),
            field_name=f"rules.multi_leg.legs[].{field_name}",
        )
        if value is not None:
            execution_overrides[field_name] = value
    min_fee_edge_bps = _sizing_value(
        row,
        fixed=leg.min_fee_edge_bps,
        column=leg.min_fee_edge_bps_column,
    )
    if min_fee_edge_bps is not None:
        execution_overrides["min_fee_edge_bps"] = min_fee_edge_bps
    for field_name in (
        "depth_column",
        "latency_column",
        "queue_position_score_column",
        "borrow_availability_column",
        "borrow_cost_column",
        "tax_drag_column",
        "turnover_pressure_column",
        "capacity_usage_column",
        "correlation_crowding_column",
        "fee_edge_column",
    ):
        value = getattr(leg, field_name)
        if value is not None:
            execution_overrides[field_name] = value
    return execution_overrides
