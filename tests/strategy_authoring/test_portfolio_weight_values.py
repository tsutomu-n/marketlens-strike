from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.portfolio_weight_values import (
    _portfolio_turnover_weight_value,
    _position_weight_value,
)


def test_position_weight_value_uses_numeric_position_weight_or_default() -> None:
    assert _position_weight_value({"position_weight": 0.4}) == 0.4
    assert _position_weight_value({"position_weight": -0.4}) == -0.4
    assert _position_weight_value({"position_weight": "0.4"}) == 1.0
    assert _position_weight_value({}) == 1.0


def test_portfolio_turnover_weight_value_prefers_absolute_turnover_override() -> None:
    assert (
        _portfolio_turnover_weight_value(
            {"_portfolio_turnover_weight": -0.8, "position_weight": 0.2}
        )
        == 0.8
    )


def test_portfolio_turnover_weight_value_falls_back_to_absolute_position_weight() -> None:
    assert _portfolio_turnover_weight_value({"position_weight": -0.3}) == 0.3
    assert _portfolio_turnover_weight_value({"position_weight": "0.3"}) == 1.0
