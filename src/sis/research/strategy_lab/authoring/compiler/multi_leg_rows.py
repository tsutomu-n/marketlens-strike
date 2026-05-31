from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.common import (
    _entry_type_value,
    _minutes_value,
    _multi_leg_group_id,
    _non_negative_bps_value,
    _non_negative_value,
    _optional_bool_from_row,
    _resolve_leg_side,
    _signal_notional_usd,
    _signal_position_weight,
    _sizing_value,
    _time_in_force_value,
    _unit_interval_value,
)
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _multi_leg_signal_rows(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    bindings: dict[str, SymbolBinding],
    base_side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
) -> list[dict[str, Any]]:
    base_weight = _sizing_value(
        row,
        fixed=_signal_position_weight(row, spec),
        column=None,
    )
    base_notional = _sizing_value(
        row,
        fixed=_signal_notional_usd(row, spec),
        column=None,
    )
    rows: list[dict[str, Any]] = []
    group_id = _multi_leg_group_id(spec, row, base_side=base_side)
    leg_count = len(spec.rules.multi_leg.legs)
    anchor_symbol = spec.rules.multi_leg.anchor_real_market_symbol
    for index, leg in enumerate(spec.rules.multi_leg.legs):
        binding = bindings[leg.real_market_symbol]
        leg_side = _resolve_leg_side(base_side, leg.side)
        leg_weight_multiplier = _sizing_value(
            row,
            fixed=leg.position_weight,
            column=leg.position_weight_column,
        )
        leg_weight = (base_weight if base_weight is not None else 1.0) * (
            leg_weight_multiplier if leg_weight_multiplier is not None else 1.0
        )
        leg_notional = _sizing_value(
            row,
            fixed=leg.notional_usd,
            column=leg.notional_usd_column,
        )
        if leg_notional is None and base_notional is not None:
            leg_notional = base_notional * (
                leg_weight_multiplier if leg_weight_multiplier is not None else leg.position_weight
            )
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
        order_overrides: dict[str, Any] = {}
        if leg.entry_type is not None or leg.entry_type_column is not None:
            order_overrides["entry_type"] = _entry_type_value(
                row,
                fixed=leg.entry_type or spec.rules.order.entry_type,
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
                fixed=leg.time_in_force or spec.rules.order.time_in_force,
                column=leg.time_in_force_column,
            )
        for field_name in ("post_only", "reduce_only"):
            column_value = _optional_bool_from_row(row, getattr(leg, f"{field_name}_column"))
            fixed_value = getattr(leg, field_name)
            value = column_value if column_value is not None else fixed_value
            if value is not None:
                order_overrides[field_name] = value
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
        rows.append(
            _trade_signal_row(
                spec=spec,
                row=row,
                binding=binding,
                side=leg_side,
                generated_at=generated_at,
                raw_score=raw_score,
                rank=rank,
                position_weight=leg_weight,
                notional_usd=leg_notional,
                exit_overrides=exit_overrides,
                order_overrides=order_overrides,
                execution_overrides=execution_overrides,
                multi_leg_group_id=group_id,
                multi_leg_leg_index=index + 1,
                multi_leg_leg_count=leg_count,
                multi_leg_anchor_real_market_symbol=anchor_symbol,
                reason_codes=[
                    spec.rules.reason_code,
                    "multi_leg",
                    leg.reason_code or f"leg_{index + 1}",
                ],
            )
        )
    return rows
