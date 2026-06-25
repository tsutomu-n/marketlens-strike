from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_exit_partial_fields import (
    _trade_exit_partial_fields,
)


def _exit(**overrides):
    defaults = {
        "partial_take_profit_bps": None,
        "partial_take_profit_bps_column": None,
        "partial_exit_fraction": None,
        "partial_exit_fraction_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_exit_partial_fields_resolve_defaults() -> None:
    assert _trade_exit_partial_fields(row={}, exit_rules=_exit()) == {
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
    }


def test_trade_exit_partial_fields_use_row_columns_regime_and_overrides() -> None:
    fields = _trade_exit_partial_fields(
        row={
            "row_partial_take": 100.0,
            "row_partial_fraction": 0.25,
        },
        exit_rules=_exit(
            partial_take_profit_bps_column="row_partial_take",
            partial_exit_fraction_column="row_partial_fraction",
        ),
        regime=_regime(
            partial_take_profit_bps=150.0,
            partial_exit_fraction=0.4,
        ),
        exit_overrides={
            "partial_take_profit_bps": 120.0,
        },
    )

    assert fields == {
        "partial_take_profit_bps": 120.0,
        "partial_exit_fraction": 0.25,
    }
