from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_borrow_fields import (
    _trade_execution_borrow_fields,
)


def _execution(**overrides):
    defaults = {
        "min_borrow_availability_ratio": None,
        "min_borrow_availability_ratio_column": None,
        "borrow_availability_column": "borrow_availability_ratio",
        "max_borrow_cost_bps": None,
        "max_borrow_cost_bps_column": None,
        "borrow_cost_column": "borrow_cost_bps",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "min_borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_execution_borrow_fields_resolve_defaults() -> None:
    assert _trade_execution_borrow_fields(row={}, execution=_execution()) == {
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
    }


def test_trade_execution_borrow_fields_use_row_columns_regime_and_overrides() -> None:
    fields = _trade_execution_borrow_fields(
        row={
            "row_min_borrow_availability": 0.9,
            "borrow_available": "0.95",
            "row_max_borrow_cost": 3.5,
            "borrow_cost_override": "2.5",
        },
        execution=_execution(
            min_borrow_availability_ratio_column="row_min_borrow_availability",
            borrow_availability_column="borrow_availability",
            max_borrow_cost_bps_column="row_max_borrow_cost",
            borrow_cost_column="borrow_cost_bps",
        ),
        regime=_regime(
            min_borrow_availability_ratio=0.5,
            max_borrow_cost_bps=6.0,
        ),
        execution_overrides={
            "borrow_availability_column": "borrow_available",
            "borrow_cost_column": "borrow_cost_override",
        },
    )

    assert fields == {
        "min_borrow_availability_ratio": 0.9,
        "borrow_availability_ratio": 0.95,
        "max_borrow_cost_bps": 3.5,
        "borrow_cost_bps": 2.5,
    }
