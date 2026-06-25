from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_exit_stop_fields import (
    _trade_exit_stop_fields,
)


def _exit(**overrides):
    defaults = {
        "stop_loss_bps": None,
        "stop_loss_bps_column": None,
        "min_stop_loss_bps": None,
        "min_stop_loss_bps_column": None,
        "max_stop_loss_bps": None,
        "max_stop_loss_bps_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_exit_stop_fields_resolve_defaults() -> None:
    assert _trade_exit_stop_fields(row={}, exit_rules=_exit()) == {
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
    }


def test_trade_exit_stop_fields_use_row_columns_regime_and_overrides() -> None:
    fields = _trade_exit_stop_fields(
        row={
            "row_stop": 999.0,
            "row_min_stop": 80.0,
            "row_max_stop": 200.0,
        },
        exit_rules=_exit(
            stop_loss_bps_column="row_stop",
            min_stop_loss_bps_column="row_min_stop",
            max_stop_loss_bps_column="row_max_stop",
        ),
        regime=_regime(stop_loss_bps=90.0),
        exit_overrides={"stop_loss_bps": 120.0},
    )

    assert fields == {
        "stop_loss_bps": 120.0,
        "min_stop_loss_bps": 80.0,
        "max_stop_loss_bps": 200.0,
    }
