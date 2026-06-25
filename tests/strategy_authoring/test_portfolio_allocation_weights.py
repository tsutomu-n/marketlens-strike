from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.portfolio_allocation_weights import (
    _allocation_raw_weights,
)


def _portfolio(**overrides):
    defaults = {"allocation_method": "equal_weight"}
    return SimpleNamespace(**{**defaults, **overrides})


def test_allocation_raw_weights_use_equal_weight_for_each_row() -> None:
    weights = _allocation_raw_weights(
        [{"raw_score": 0.9}, {"raw_score": 0.1}, {"raw_score": None}],
        _portfolio(allocation_method="equal_weight"),
    )

    assert weights == [1.0, 1.0, 1.0]


def test_allocation_raw_weights_use_positive_scores_or_equal_fallback() -> None:
    assert _allocation_raw_weights(
        [
            {"raw_score": 0.6},
            {"raw_score": -1.0},
            {"raw_score": None},
        ],
        _portfolio(allocation_method="score_proportional"),
    ) == [0.6, 0.0, 0.0]
    assert _allocation_raw_weights(
        [
            {"raw_score": -1.0},
            {"raw_score": None},
            {"raw_score": 0.0},
        ],
        _portfolio(allocation_method="score_proportional"),
    ) == [1.0, 1.0, 1.0]


def test_allocation_raw_weights_use_inverse_volatility_or_equal_fallback() -> None:
    assert _allocation_raw_weights(
        [
            {"_allocation_volatility": 0.5},
            {"_allocation_volatility": 1.0},
            {"_allocation_volatility": 0.0},
            {"_allocation_volatility": None},
        ],
        _portfolio(allocation_method="inverse_volatility"),
    ) == [2.0, 1.0, 0.0, 0.0]
    assert _allocation_raw_weights(
        [
            {"_allocation_volatility": 0.0},
            {"_allocation_volatility": None},
            {"_allocation_volatility": -1.0},
        ],
        _portfolio(allocation_method="inverse_volatility"),
    ) == [1.0, 1.0, 1.0]
