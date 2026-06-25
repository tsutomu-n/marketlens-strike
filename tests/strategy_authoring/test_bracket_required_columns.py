from __future__ import annotations

from sis.research.strategy_lab.authoring.bracket_required_columns import (
    _bracket_required_columns,
)
from sis.research.strategy_lab.authoring.contracts.trade_controls import BracketRules


def test_bracket_required_columns_collects_explicit_bracket_columns() -> None:
    rules = BracketRules(
        time_stop_minutes_column="row_time_stop",
        break_even_after_bps_column="row_break_even",
    )

    assert _bracket_required_columns(rules, derived_names=set()) == {
        "row_time_stop",
        "row_break_even",
    }


def test_bracket_required_columns_returns_empty_set_when_disabled() -> None:
    assert _bracket_required_columns(BracketRules(), derived_names=set()) == set()


def test_bracket_required_columns_ignores_derived_outputs() -> None:
    rules = BracketRules(
        time_stop_minutes_column="row_time_stop",
        break_even_after_bps_column="row_break_even",
    )

    assert (
        _bracket_required_columns(
            rules,
            derived_names={"row_time_stop", "row_break_even"},
        )
        == set()
    )
