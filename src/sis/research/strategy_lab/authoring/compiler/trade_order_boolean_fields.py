from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
)
from sis.research.strategy_lab.authoring.compiler.order_row_values import _optional_bool_from_row


def _order_boolean_value(
    *,
    row: dict[str, Any],
    order: Any,
    order_overrides: dict[str, Any] | None,
    value_attr: str,
    column_attr: str,
) -> bool:
    column = _override_column(order_overrides, value_attr, getattr(order, column_attr))
    row_value = _optional_bool_from_row(row, column) if column is not None else None
    if row_value is not None:
        return row_value
    return bool(_override_value(order_overrides, value_attr, getattr(order, value_attr)))
