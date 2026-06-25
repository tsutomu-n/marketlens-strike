from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.reward_risk import _reward_risk_ratio


def test_reward_risk_ratio_uses_take_profit_over_stop_loss() -> None:
    assert _reward_risk_ratio({"stop_loss_bps": 150.0, "take_profit_bps": 300.0}) == 2.0


def test_reward_risk_ratio_returns_none_for_missing_or_invalid_stop() -> None:
    assert _reward_risk_ratio({"take_profit_bps": 300.0}) is None
    assert _reward_risk_ratio({"stop_loss_bps": 150.0}) is None
    assert _reward_risk_ratio({"stop_loss_bps": 0.0, "take_profit_bps": 300.0}) is None
    assert _reward_risk_ratio({"stop_loss_bps": -10.0, "take_profit_bps": 300.0}) is None
