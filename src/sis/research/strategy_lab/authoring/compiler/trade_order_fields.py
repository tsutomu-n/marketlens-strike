from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
)
from sis.research.strategy_lab.authoring.compiler.order_row_values import (
    _entry_type_value,
    _time_in_force_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _minutes_value,
    _non_negative_bps_value,
)
from sis.research.strategy_lab.authoring.compiler.trade_order_boolean_fields import (
    _order_boolean_value,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _trade_order_fields(
    *,
    row: dict[str, Any],
    order: Any,
    order_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reduce_only = _order_boolean_value(
        row=row,
        order=order,
        order_overrides=order_overrides,
        value_attr="reduce_only",
        column_attr="reduce_only_column",
    )
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
    entry_order_type = _entry_type_value(
        row,
        fixed=_override_value(order_overrides, "entry_type", order.entry_type),
        column=_override_column(order_overrides, "entry_type", order.entry_type_column),
    )
    entry_limit_offset_bps = _non_negative_bps_value(
        row,
        fixed=_override_value(order_overrides, "limit_offset_bps", order.limit_offset_bps),
        column=_override_column(order_overrides, "limit_offset_bps", order.limit_offset_bps_column),
        field_name="rules.order.limit_offset_bps",
    )
    entry_stop_offset_bps = _non_negative_bps_value(
        row,
        fixed=_override_value(order_overrides, "stop_offset_bps", order.stop_offset_bps),
        column=_override_column(order_overrides, "stop_offset_bps", order.stop_offset_bps_column),
        field_name="rules.order.stop_offset_bps",
    )
    if entry_order_type == "limit" and entry_limit_offset_bps is None:
        raise StrategyAuthoringValidationError(
            "rules.order.limit_offset_bps or limit_offset_bps_column is required "
            "when row entry_type is limit"
        )
    if entry_order_type == "stop_market" and entry_stop_offset_bps is None:
        raise StrategyAuthoringValidationError(
            "rules.order.stop_offset_bps or stop_offset_bps_column is required "
            "when row entry_type is stop_market"
        )
    post_only = _order_boolean_value(
        row=row,
        order=order,
        order_overrides=order_overrides,
        value_attr="post_only",
        column_attr="post_only_column",
    )
    if post_only and entry_order_type != "limit":
        raise StrategyAuthoringValidationError(
            "rules.order.post_only is only supported for limit entry"
        )
    return {
        "entry_order_type": entry_order_type,
        "entry_limit_offset_bps": entry_limit_offset_bps,
        "entry_stop_offset_bps": entry_stop_offset_bps,
        "entry_timeout_minutes": entry_timeout_minutes,
        "entry_time_in_force": entry_time_in_force,
        "entry_post_only": post_only,
        "entry_reduce_only": reduce_only,
    }
