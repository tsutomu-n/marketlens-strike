from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.portfolio_timestamp_limits import (
    _PORTFOLIO_LIMIT_SPECS,
    _PortfolioLimitSpec,
    _portfolio_limit_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def test_portfolio_limit_specs_map_public_limit_names() -> None:
    assert _PORTFOLIO_LIMIT_SPECS["max_total_position_weight"] == _PortfolioLimitSpec(
        fixed_attr="max_total_position_weight",
        value_key="_portfolio_max_total_position_weight",
        field_name="rules.portfolio.max_total_position_weight_column",
    )
    assert _PORTFOLIO_LIMIT_SPECS["max_group_abs_net_position_weight"] == _PortfolioLimitSpec(
        fixed_attr="max_group_abs_net_position_weight",
        value_key="_portfolio_max_group_abs_net_position_weight",
        field_name="rules.portfolio.max_group_abs_net_position_weight_column",
    )


def test_portfolio_limit_value_uses_dynamic_row_value_before_fixed_value() -> None:
    value = _portfolio_limit_value(
        [{"_portfolio_max_total_position_weight": 0.7}],
        portfolio=SimpleNamespace(max_total_position_weight=1.0),
        spec=_PORTFOLIO_LIMIT_SPECS["max_total_position_weight"],
    )

    assert value == 0.7


def test_portfolio_limit_value_uses_fixed_value_when_rows_are_missing() -> None:
    value = _portfolio_limit_value(
        [{"_portfolio_max_total_position_weight": None}, {"other": 1.0}],
        portfolio=SimpleNamespace(max_total_position_weight=1.0),
        spec=_PORTFOLIO_LIMIT_SPECS["max_total_position_weight"],
    )

    assert value == 1.0


def test_portfolio_limit_value_preserves_error_field_names() -> None:
    spec = _PORTFOLIO_LIMIT_SPECS["max_total_position_weight"]

    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.portfolio.max_total_position_weight_column must be >= 0",
    ):
        _portfolio_limit_value(
            [{"_portfolio_max_total_position_weight": -0.1}],
            portfolio=SimpleNamespace(max_total_position_weight=1.0),
            spec=spec,
        )
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.portfolio.max_total_position_weight_column must resolve to one value",
    ):
        _portfolio_limit_value(
            [
                {"_portfolio_max_total_position_weight": 0.7},
                {"_portfolio_max_total_position_weight": 0.8},
            ],
            portfolio=SimpleNamespace(max_total_position_weight=1.0),
            spec=spec,
        )
