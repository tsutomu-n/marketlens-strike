from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_pressure_values import (
    _execution_pressure_limit_value,
    _execution_pressure_observed_value,
)


def _execution(**overrides):
    defaults = {
        "max_turnover_pressure": 0.9,
        "max_turnover_pressure_column": "row_limit",
        "turnover_pressure_column": "turnover_pressure",
        "fee_edge_column": "fee_edge_bps",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "max_turnover_pressure": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_execution_pressure_limit_value_uses_row_column_before_fixed_values() -> None:
    value = _execution_pressure_limit_value(
        row={"row_limit": "0.4"},
        execution=_execution(),
        regime=_regime(max_turnover_pressure=0.7),
        execution_overrides=None,
        value_attr="max_turnover_pressure",
        column_attr="max_turnover_pressure_column",
    )

    assert value == 0.4


def test_execution_pressure_limit_value_uses_explicit_override_and_disables_column() -> None:
    value = _execution_pressure_limit_value(
        row={"row_limit": 0.4},
        execution=_execution(),
        regime=_regime(max_turnover_pressure=0.7),
        execution_overrides={"max_turnover_pressure": 0.2},
        value_attr="max_turnover_pressure",
        column_attr="max_turnover_pressure_column",
    )

    assert value == 0.2


def test_execution_pressure_limit_value_falls_back_to_regime_then_execution() -> None:
    assert (
        _execution_pressure_limit_value(
            row={},
            execution=_execution(max_turnover_pressure=0.9),
            regime=_regime(max_turnover_pressure=0.7),
            execution_overrides=None,
            value_attr="max_turnover_pressure",
            column_attr="max_turnover_pressure_column",
        )
        == 0.7
    )
    assert (
        _execution_pressure_limit_value(
            row={},
            execution=_execution(max_turnover_pressure=0.9),
            regime=None,
            execution_overrides=None,
            value_attr="max_turnover_pressure",
            column_attr="max_turnover_pressure_column",
        )
        == 0.9
    )


def test_execution_pressure_observed_value_uses_override_column() -> None:
    value = _execution_pressure_observed_value(
        row={"fee_edge_override": "-1.25", "fee_edge_bps": 0.5},
        execution=_execution(),
        execution_overrides={"fee_edge_column": "fee_edge_override"},
        override_column_key="fee_edge_column",
        column_attr="fee_edge_column",
    )

    assert value == -1.25


def test_execution_pressure_observed_value_returns_none_without_resolved_column_value() -> None:
    value = _execution_pressure_observed_value(
        row={},
        execution=_execution(turnover_pressure_column="turnover_pressure"),
        execution_overrides=None,
        override_column_key="turnover_pressure_column",
        column_attr="turnover_pressure_column",
    )

    assert value is None
