from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.portfolio_allocation import (
    _allocation_raw_weights,
    _neutral_allocated_rows,
    _portfolio_target_total_position_weight,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def _portfolio(**overrides):
    defaults = {
        "allocation_method": "equal_weight",
        "target_total_position_weight": 1.0,
        "target_total_position_weight_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_allocation_raw_weights_fallback_when_scores_are_not_positive() -> None:
    weights = _allocation_raw_weights(
        [
            {"raw_score": -1.0},
            {"raw_score": None},
            {"raw_score": 0.0},
        ],
        _portfolio(allocation_method="score_proportional"),
    )

    assert weights == [1.0, 1.0, 1.0]


def test_allocation_raw_weights_use_inverse_volatility_when_available() -> None:
    weights = _allocation_raw_weights(
        [
            {"_allocation_volatility": 0.5},
            {"_allocation_volatility": 1.0},
            {"_allocation_volatility": 0.0},
        ],
        _portfolio(allocation_method="inverse_volatility"),
    )

    assert weights == [2.0, 1.0, 0.0]


def test_neutral_allocated_rows_balance_long_and_short_gross() -> None:
    rows = _neutral_allocated_rows(
        [
            {"side": "long", "position_weight": 2.0, "rank_score": 0.9},
            {"side": "long", "position_weight": 1.0, "rank_score": 0.8},
            {"side": "short", "position_weight": 3.0, "rank_score": 0.7},
        ],
        target=1.2,
        method="dollar_neutral",
    )

    assert [row["position_weight"] for row in rows] == pytest.approx([0.4, 0.2, 0.6])


def test_portfolio_target_total_position_weight_resolves_one_row_value() -> None:
    target = _portfolio_target_total_position_weight(
        [
            {"_portfolio_target_total_position_weight": 0.8},
            {"_portfolio_target_total_position_weight": 0.8},
        ],
        _portfolio(target_total_position_weight=1.0, target_total_position_weight_column="target"),
    )

    assert target == 0.8


def test_portfolio_target_total_position_weight_rejects_mixed_row_values() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="target_total_position_weight_column must resolve to one value",
    ):
        _portfolio_target_total_position_weight(
            [
                {"_portfolio_target_total_position_weight": 0.8},
                {"_portfolio_target_total_position_weight": 0.9},
            ],
            _portfolio(
                target_total_position_weight=1.0,
                target_total_position_weight_column="target",
            ),
        )
