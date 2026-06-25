from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_tax_fields import (
    _trade_execution_tax_fields,
)


def _execution(**overrides):
    defaults = {
        "max_tax_drag_bps": None,
        "max_tax_drag_bps_column": None,
        "tax_drag_column": "tax_drag_bps",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {"max_tax_drag_bps": None}
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_execution_tax_fields_resolve_defaults() -> None:
    assert _trade_execution_tax_fields(row={}, execution=_execution()) == {
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
    }


def test_trade_execution_tax_fields_use_row_columns_regime_and_overrides() -> None:
    fields = _trade_execution_tax_fields(
        row={
            "row_max_tax_drag": 1.2,
            "tax_drag_override": "0.8",
        },
        execution=_execution(
            max_tax_drag_bps_column="row_max_tax_drag",
            tax_drag_column="tax_drag_bps",
        ),
        regime=_regime(max_tax_drag_bps=4.0),
        execution_overrides={"tax_drag_column": "tax_drag_override"},
    )

    assert fields == {
        "max_tax_drag_bps": 1.2,
        "tax_drag_bps": 0.8,
    }
