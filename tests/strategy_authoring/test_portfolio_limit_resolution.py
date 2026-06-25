from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.portfolio_limit_resolution import (
    _portfolio_max_abs_net_position_weight,
    _portfolio_max_group_abs_net_position_weight,
    _portfolio_max_total_position_weight,
    _portfolio_timestamp_limit,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def _portfolio(**overrides):
    defaults = {
        "max_total_position_weight": None,
        "max_total_position_weight_column": None,
        "max_abs_net_position_weight": None,
        "max_abs_net_position_weight_column": None,
        "max_group_abs_net_position_weight": None,
        "max_group_abs_net_position_weight_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_portfolio_timestamp_limit_uses_fixed_value_when_rows_are_missing() -> None:
    limit = _portfolio_timestamp_limit(
        [{"_limit": None}, {"other": 1.0}],
        fixed=0.7,
        value_key="_limit",
        field_name="rules.portfolio.limit_column",
    )

    assert limit == 0.7


def test_portfolio_timestamp_limit_uses_single_row_value() -> None:
    limit = _portfolio_timestamp_limit(
        [{"_limit": 0.6}, {"_limit": 0.6}],
        fixed=0.7,
        value_key="_limit",
        field_name="rules.portfolio.limit_column",
    )

    assert limit == 0.6


def test_portfolio_timestamp_limit_rejects_mixed_row_values() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.portfolio.limit_column must resolve to one value per timestamp",
    ):
        _portfolio_timestamp_limit(
            [{"_limit": 0.6}, {"_limit": 0.7}],
            fixed=0.9,
            value_key="_limit",
            field_name="rules.portfolio.limit_column",
        )


def test_portfolio_timestamp_limit_rejects_negative_row_value() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.portfolio.limit_column must be >= 0",
    ):
        _portfolio_timestamp_limit(
            [{"_limit": -0.1}],
            fixed=0.9,
            value_key="_limit",
            field_name="rules.portfolio.limit_column",
        )


def test_portfolio_exposure_limit_helpers_resolve_dynamic_values() -> None:
    rows = [
        {
            "_portfolio_max_total_position_weight": 1.0,
            "_portfolio_max_abs_net_position_weight": 0.4,
            "_portfolio_max_group_abs_net_position_weight": 0.3,
        }
    ]
    portfolio = _portfolio(
        max_total_position_weight=2.0,
        max_total_position_weight_column="max_total",
        max_abs_net_position_weight=1.0,
        max_abs_net_position_weight_column="max_net",
        max_group_abs_net_position_weight=0.8,
        max_group_abs_net_position_weight_column="max_group_net",
    )

    assert _portfolio_max_total_position_weight(rows, portfolio) == 1.0
    assert _portfolio_max_abs_net_position_weight(rows, portfolio) == 0.4
    assert _portfolio_max_group_abs_net_position_weight(rows, portfolio) == 0.3
