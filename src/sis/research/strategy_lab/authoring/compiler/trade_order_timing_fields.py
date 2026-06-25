from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
)
from sis.research.strategy_lab.authoring.compiler.order_row_values import _time_in_force_value
from sis.research.strategy_lab.authoring.compiler.row_values import _minutes_value
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _trade_order_timing_fields(
    *,
    row: dict[str, Any],
    order: Any,
    order_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry_timeout_minutes = _minutes_value(
        row,
        fixed=_override_value(order_overrides, "timeout_minutes", order.timeout_minutes),
        column=_override_column(order_overrides, "timeout_minutes", order.timeout_minutes_column),
    )
    entry_time_in_force = _time_in_force_value(
        row,
        fixed=_override_value(order_overrides, "time_in_force", order.time_in_force),
        column=_override_column(order_overrides, "time_in_force", order.time_in_force_column),
    )
    if entry_time_in_force == "gtd" and entry_timeout_minutes is None:
        raise StrategyAuthoringValidationError(
            "rules.order.timeout_minutes or timeout_minutes_column is required "
            "when row time_in_force is gtd"
        )
    if entry_time_in_force in {"ioc", "fok"} and entry_timeout_minutes is not None:
        raise StrategyAuthoringValidationError(
            "rules.order.timeout_minutes cannot be set when row time_in_force is ioc or fok"
        )
    return {
        "entry_timeout_minutes": entry_timeout_minutes,
        "entry_time_in_force": entry_time_in_force,
    }
