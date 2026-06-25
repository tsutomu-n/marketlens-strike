from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_values import (
    _non_negative_bps_value,
    _non_negative_value,
    _unit_interval_value,
)
from sis.research.strategy_lab.authoring.compiler.multi_leg_execution_overrides import (
    _multi_leg_execution_overrides as _multi_leg_execution_overrides,
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
