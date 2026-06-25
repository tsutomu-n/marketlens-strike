from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import OrderRules
from sis.research.strategy_lab.authoring.order_required_columns import (
    _order_required_columns,
)


def test_order_required_columns_collects_explicit_order_columns() -> None:
    rules = OrderRules(
        entry_type_column="entry_type",
        limit_offset_bps_column="limit_offset",
        stop_offset_bps_column="stop_offset",
        timeout_minutes_column="timeout",
        time_in_force_column="tif",
        post_only_column="post_only",
        reduce_only_column="reduce_only",
    )

    assert _order_required_columns(rules) == {
        "entry_type",
        "limit_offset",
        "stop_offset",
        "timeout",
        "tif",
        "post_only",
        "reduce_only",
    }


def test_order_required_columns_returns_empty_set_when_disabled() -> None:
    assert _order_required_columns(OrderRules()) == set()
