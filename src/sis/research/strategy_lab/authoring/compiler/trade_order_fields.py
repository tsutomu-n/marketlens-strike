from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.trade_order_boolean_fields import (
    _order_boolean_value,
)
from sis.research.strategy_lab.authoring.compiler.trade_order_price_fields import (
    _trade_order_price_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_order_timing_fields import (
    _trade_order_timing_fields,
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
    timing_fields = _trade_order_timing_fields(
        row=row,
        order=order,
        order_overrides=order_overrides,
    )
    price_fields = _trade_order_price_fields(
        row=row,
        order=order,
        order_overrides=order_overrides,
    )
    entry_order_type = str(price_fields["entry_order_type"])
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
        **price_fields,
        **timing_fields,
        "entry_post_only": post_only,
        "entry_reduce_only": reduce_only,
    }
