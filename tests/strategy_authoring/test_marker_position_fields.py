from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.marker_position_fields import (
    _marker_add_fields,
    _marker_rebalance_fields,
    _marker_reduce_fields,
)


def _spec(**overrides):
    defaults = {
        "reduce_fraction": 0.5,
        "reduce_fraction_column": None,
        "add_fraction": 0.25,
        "add_fraction_column": None,
        "rebalance_target_fraction": 0.8,
        "rebalance_target_fraction_column": None,
        "rebalance_min_delta_fraction": 0.1,
        "rebalance_min_delta_fraction_column": None,
    }
    return SimpleNamespace(rules=SimpleNamespace(exit=SimpleNamespace(**{**defaults, **overrides})))


def test_marker_position_fields_use_fixed_values() -> None:
    spec = _spec()

    assert _marker_reduce_fields(row={}, spec=spec) == {"reduce_fraction": 0.5}
    assert _marker_add_fields(row={}, spec=spec) == {"add_fraction": 0.25}
    assert _marker_rebalance_fields(row={}, spec=spec) == {
        "rebalance_target_fraction": 0.8,
        "rebalance_min_delta_fraction": 0.1,
    }


def test_marker_position_fields_use_row_column_values() -> None:
    spec = _spec(
        reduce_fraction=None,
        reduce_fraction_column="row_reduce",
        add_fraction=None,
        add_fraction_column="row_add",
        rebalance_target_fraction=None,
        rebalance_target_fraction_column="row_target",
        rebalance_min_delta_fraction=None,
        rebalance_min_delta_fraction_column="row_min_delta",
    )
    row = {
        "row_reduce": 0.4,
        "row_add": 0.3,
        "row_target": 0.9,
        "row_min_delta": 0.2,
    }

    assert _marker_reduce_fields(row=row, spec=spec) == {"reduce_fraction": 0.4}
    assert _marker_add_fields(row=row, spec=spec) == {"add_fraction": 0.3}
    assert _marker_rebalance_fields(row=row, spec=spec) == {
        "rebalance_target_fraction": 0.9,
        "rebalance_min_delta_fraction": 0.2,
    }
