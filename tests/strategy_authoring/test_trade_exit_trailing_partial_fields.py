from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_exit_trailing_partial_fields import (
    _trade_exit_trailing_partial_fields,
)


def _exit(**overrides):
    defaults = {
        "trailing_stop_bps": None,
        "trailing_stop_bps_column": None,
        "trailing_stop_activation_bps": None,
        "trailing_stop_activation_bps_column": None,
        "partial_take_profit_bps": None,
        "partial_take_profit_bps_column": None,
        "partial_exit_fraction": None,
        "partial_exit_fraction_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_exit_trailing_partial_fields_resolve_defaults() -> None:
    assert _trade_exit_trailing_partial_fields(row={}, exit_rules=_exit()) == {
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
    }


def test_trade_exit_trailing_partial_fields_use_row_columns_regime_and_overrides() -> None:
    fields = _trade_exit_trailing_partial_fields(
        row={
            "row_trailing": 50.0,
            "row_trailing_activation": 10.0,
            "row_partial_take": 100.0,
            "row_partial_fraction": 0.25,
        },
        exit_rules=_exit(
            trailing_stop_bps_column="row_trailing",
            trailing_stop_activation_bps_column="row_trailing_activation",
            partial_take_profit_bps_column="row_partial_take",
            partial_exit_fraction_column="row_partial_fraction",
        ),
        regime=_regime(
            trailing_stop_bps=70.0,
            trailing_stop_activation_bps=20.0,
            partial_take_profit_bps=150.0,
            partial_exit_fraction=0.4,
        ),
        exit_overrides={
            "trailing_stop_bps": 60.0,
            "partial_take_profit_bps": 120.0,
        },
    )

    assert fields == {
        "trailing_stop_bps": 60.0,
        "trailing_stop_activation_bps": 10.0,
        "partial_take_profit_bps": 120.0,
        "partial_exit_fraction": 0.25,
    }
