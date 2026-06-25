from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_bracket_fields import (
    _trade_bracket_fields,
)


def _bracket(**overrides):
    defaults = {
        "enabled": False,
        "bracket_type": "oco",
        "time_stop_minutes": None,
        "time_stop_minutes_column": None,
        "break_even_after_bps": None,
        "break_even_after_bps_column": None,
        "break_even_after_partial_take_profit": False,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_bracket_fields_resolve_disabled_defaults() -> None:
    assert _trade_bracket_fields(row={}, bracket=_bracket()) == {
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "bracket_break_even_after_partial_take_profit": False,
    }


def test_trade_bracket_fields_use_enabled_fixed_and_column_values() -> None:
    fields = _trade_bracket_fields(
        row={
            "row_time_stop": "45",
            "row_break_even_after": "12.5",
        },
        bracket=_bracket(
            enabled=True,
            bracket_type="oco",
            time_stop_minutes=30,
            time_stop_minutes_column="row_time_stop",
            break_even_after_bps=20.0,
            break_even_after_bps_column="row_break_even_after",
            break_even_after_partial_take_profit=True,
        ),
    )

    assert fields == {
        "bracket_type": "oco",
        "bracket_time_stop_minutes": 45,
        "bracket_break_even_after_bps": 12.5,
        "bracket_break_even_after_partial_take_profit": True,
    }
