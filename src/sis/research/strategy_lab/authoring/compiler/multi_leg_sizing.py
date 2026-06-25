from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_numeric_values import _sizing_value


def _multi_leg_sizing_fields(
    *,
    row: dict[str, Any],
    leg: Any,
    base_weight: float | None,
    base_notional: float | None,
) -> dict[str, float | None]:
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
    return {
        "position_weight": leg_weight,
        "notional_usd": leg_notional,
    }
