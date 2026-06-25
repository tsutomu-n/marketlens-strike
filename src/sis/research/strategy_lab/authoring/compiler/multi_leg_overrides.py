from __future__ import annotations

from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.row_values import (
    _entry_type_value,
    _minutes_value,
    _non_negative_bps_value,
    _non_negative_value,
    _optional_bool_from_row,
    _sizing_value,
    _time_in_force_value,
    _unit_interval_value,
)


def _multi_leg_exit_overrides(*, row: dict[str, Any], leg: Any) -> dict[str, float | None]:
    exit_overrides: dict[str, float | None] = {}
    for field_name in (
        "stop_loss_bps",
        "min_stop_loss_bps",
        "max_stop_loss_bps",
        "take_profit_bps",
        "min_take_profit_bps",
        "max_take_profit_bps",
        "trailing_stop_bps",
        "trailing_stop_activation_bps",
        "partial_take_profit_bps",
    ):
        value = _non_negative_bps_value(
            row,
            fixed=getattr(leg, field_name),
            column=getattr(leg, f"{field_name}_column"),
            field_name=f"rules.multi_leg.legs[].{field_name}",
        )
        if value is not None:
            exit_overrides[field_name] = value
    partial_exit_fraction = _unit_interval_value(
        row,
        fixed=leg.partial_exit_fraction,
        column=leg.partial_exit_fraction_column,
        field_name="rules.multi_leg.legs[].partial_exit_fraction",
    )
    if partial_exit_fraction is not None:
        exit_overrides["partial_exit_fraction"] = partial_exit_fraction
    min_reward_risk_ratio = _non_negative_value(
        row,
        fixed=leg.min_reward_risk_ratio,
        column=leg.min_reward_risk_ratio_column,
        field_name="rules.multi_leg.legs[].min_reward_risk_ratio",
    )
    if min_reward_risk_ratio is not None:
        exit_overrides["min_reward_risk_ratio"] = min_reward_risk_ratio
    return exit_overrides


def _multi_leg_order_overrides(
    *,
    row: dict[str, Any],
    leg: Any,
    default_entry_type: Literal["market", "limit", "stop_market"],
    default_time_in_force: Literal["gtc", "gtd", "ioc", "fok"],
) -> dict[str, Any]:
    order_overrides: dict[str, Any] = {}
    if leg.entry_type is not None or leg.entry_type_column is not None:
        order_overrides["entry_type"] = _entry_type_value(
            row,
            fixed=leg.entry_type or default_entry_type,
            column=leg.entry_type_column,
        )
    for field_name in ("limit_offset_bps", "stop_offset_bps"):
        value = _non_negative_bps_value(
            row,
            fixed=getattr(leg, field_name),
            column=getattr(leg, f"{field_name}_column"),
            field_name=f"rules.multi_leg.legs[].{field_name}",
        )
        if value is not None:
            order_overrides[field_name] = value
    timeout_minutes = _minutes_value(
        row,
        fixed=leg.timeout_minutes,
        column=leg.timeout_minutes_column,
    )
    if timeout_minutes is not None:
        order_overrides["timeout_minutes"] = timeout_minutes
    if leg.time_in_force is not None or leg.time_in_force_column is not None:
        order_overrides["time_in_force"] = _time_in_force_value(
            row,
            fixed=leg.time_in_force or default_time_in_force,
            column=leg.time_in_force_column,
        )
    for field_name in ("post_only", "reduce_only"):
        column_value = _optional_bool_from_row(row, getattr(leg, f"{field_name}_column"))
        fixed_value = getattr(leg, field_name)
        value = column_value if column_value is not None else fixed_value
        if value is not None:
            order_overrides[field_name] = value
    return order_overrides


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
