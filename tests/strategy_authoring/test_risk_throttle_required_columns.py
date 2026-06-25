from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.risk_controls import RiskThrottleRules
from sis.research.strategy_lab.authoring.risk_throttle_required_columns import (
    _risk_throttle_required_columns,
)


def test_risk_throttle_required_columns_collects_explicit_threshold_columns() -> None:
    rules = RiskThrottleRules(
        max_drawdown_column="drawdown",
        max_drawdown_floor_column="drawdown_floor",
        daily_loss_column="daily_loss",
        daily_loss_floor_column="daily_floor",
        loss_streak_column="loss_streak",
        max_loss_streak_column="loss_streak_cap",
    )

    assert _risk_throttle_required_columns(rules) == {
        "drawdown",
        "drawdown_floor",
        "daily_loss",
        "daily_floor",
        "loss_streak",
        "loss_streak_cap",
    }


def test_risk_throttle_required_columns_returns_empty_set_when_disabled() -> None:
    assert _risk_throttle_required_columns(RiskThrottleRules()) == set()


def test_risk_throttle_required_columns_collects_profile_defaults() -> None:
    rules = RiskThrottleRules(profile="conservative")

    assert _risk_throttle_required_columns(rules) == {
        "strategy_drawdown",
        "daily_pnl",
        "loss_streak",
    }
