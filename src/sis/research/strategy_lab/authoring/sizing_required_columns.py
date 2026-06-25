from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import SizingRules


def _sizing_required_columns(sizing: SizingRules) -> set[str]:
    columns: set[str] = set()
    for column_name in (
        sizing.position_weight_column,
        sizing.notional_usd_column,
        sizing.volatility_column,
    ):
        if column_name is not None:
            columns.add(column_name)
    return columns
