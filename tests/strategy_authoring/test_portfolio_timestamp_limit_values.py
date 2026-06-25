from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.portfolio_timestamp_limit_values import (
    _portfolio_timestamp_limit_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def test_portfolio_timestamp_limit_value_returns_none_without_numeric_rows() -> None:
    assert (
        _portfolio_timestamp_limit_value(
            [{"_limit": None}, {"_limit": "0.7"}, {"other": 1.0}],
            value_key="_limit",
            field_name="rules.portfolio.limit_column",
        )
        is None
    )


def test_portfolio_timestamp_limit_value_uses_one_numeric_value_per_timestamp() -> None:
    assert (
        _portfolio_timestamp_limit_value(
            [{"_limit": 0.6}, {"_limit": 0.6 + 5e-13}],
            value_key="_limit",
            field_name="rules.portfolio.limit_column",
        )
        == 0.6
    )


def test_portfolio_timestamp_limit_value_rejects_negative_or_mixed_values() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.portfolio.limit_column must be >= 0",
    ):
        _portfolio_timestamp_limit_value(
            [{"_limit": -0.1}],
            value_key="_limit",
            field_name="rules.portfolio.limit_column",
        )

    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.portfolio.limit_column must resolve to one value per timestamp",
    ):
        _portfolio_timestamp_limit_value(
            [{"_limit": 0.6}, {"_limit": 0.7}],
            value_key="_limit",
            field_name="rules.portfolio.limit_column",
        )
