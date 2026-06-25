from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.portfolio_neutral_allocation import (
    _neutral_allocated_rows,
)


def test_neutral_allocated_rows_balance_dollar_neutral_gross() -> None:
    rows = _neutral_allocated_rows(
        [
            {"side": "long", "position_weight": 2.0},
            {"side": "long", "position_weight": 1.0},
            {"side": "short", "position_weight": 3.0},
        ],
        target=1.2,
        method="dollar_neutral",
    )

    assert [row["position_weight"] for row in rows] == pytest.approx([0.4, 0.2, 0.6])


def test_neutral_allocated_rows_balance_beta_exposure() -> None:
    rows = _neutral_allocated_rows(
        [
            {"side": "long", "position_weight": 1.0, "_allocation_beta": 2.0},
            {"side": "short", "position_weight": 1.0, "_allocation_beta": 1.0},
        ],
        target=1.2,
        method="beta_neutral",
    )

    assert [row["position_weight"] for row in rows] == pytest.approx([0.4, 0.8])


def test_neutral_allocated_rows_balance_each_group_and_zero_ungrouped_rows() -> None:
    rows = _neutral_allocated_rows(
        [
            {"side": "long", "position_weight": 2.0, "_portfolio_group": "tech"},
            {"side": "short", "position_weight": 1.0, "_portfolio_group": "tech"},
            {"side": "long", "position_weight": 1.0, "_portfolio_group": "energy"},
            {"side": "short", "position_weight": 3.0, "_portfolio_group": "energy"},
            {"side": "long", "position_weight": 5.0, "_portfolio_group": ""},
        ],
        target=1.2,
        method="group_neutral",
    )

    assert [row["position_weight"] for row in rows] == pytest.approx([0.3, 0.3, 0.3, 0.3, 0.0])
