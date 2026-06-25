from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_exit_take_profit_fields import (
    _trade_exit_take_profit_fields,
)


def _exit(**overrides):
    defaults = {
        "take_profit_bps": None,
        "take_profit_bps_column": None,
        "min_take_profit_bps": None,
        "min_take_profit_bps_column": None,
        "max_take_profit_bps": None,
        "max_take_profit_bps_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_exit_take_profit_fields_resolve_defaults() -> None:
    assert _trade_exit_take_profit_fields(row={}, exit_rules=_exit()) == {
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
    }


def test_trade_exit_take_profit_fields_use_row_columns_regime_and_overrides() -> None:
    fields = _trade_exit_take_profit_fields(
        row={
            "row_take": 888.0,
            "row_min_take": 250.0,
            "row_max_take": 400.0,
        },
        exit_rules=_exit(
            take_profit_bps_column="row_take",
            min_take_profit_bps_column="row_min_take",
            max_take_profit_bps_column="row_max_take",
        ),
        regime=_regime(take_profit_bps=180.0),
        exit_overrides={"take_profit_bps": 220.0},
    )

    assert fields == {
        "take_profit_bps": 220.0,
        "min_take_profit_bps": 250.0,
        "max_take_profit_bps": 400.0,
    }
