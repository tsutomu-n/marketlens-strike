from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import BracketRules


def _bracket_required_columns(bracket: BracketRules, derived_names: set[str]) -> set[str]:
    columns: set[str] = set()
    for column_name in (
        bracket.time_stop_minutes_column,
        bracket.break_even_after_bps_column,
    ):
        if column_name is not None and column_name not in derived_names:
            columns.add(column_name)
    return columns
