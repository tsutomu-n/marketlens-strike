from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
)
from sis.research.strategy_lab.authoring.compiler.order_row_values import _entry_type_value
from sis.research.strategy_lab.authoring.compiler.row_numeric_values import (
    _non_negative_bps_value,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _trade_order_price_fields(
    *,
    row: dict[str, Any],
    order: Any,
    order_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    return {
        "entry_order_type": entry_order_type,
        "entry_limit_offset_bps": entry_limit_offset_bps,
        "entry_stop_offset_bps": entry_stop_offset_bps,
    }
