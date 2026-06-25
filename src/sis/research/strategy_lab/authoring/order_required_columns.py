from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import OrderRules


def _order_required_columns(order: OrderRules) -> set[str]:
    columns: set[str] = set()
    for column_name in (
        order.entry_type_column,
        order.limit_offset_bps_column,
        order.stop_offset_bps_column,
        order.timeout_minutes_column,
        order.time_in_force_column,
        order.post_only_column,
        order.reduce_only_column,
    ):
        if column_name is not None:
            columns.add(column_name)
    return columns
