from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.risk_controls import RiskThrottleRules


def _risk_throttle_required_columns(risk_throttle: RiskThrottleRules) -> set[str]:
    columns: set[str] = set()
    for column_name in (
        risk_throttle.max_drawdown_column,
        risk_throttle.max_drawdown_floor_column,
        risk_throttle.daily_loss_column,
        risk_throttle.daily_loss_floor_column,
        risk_throttle.loss_streak_column,
        risk_throttle.max_loss_streak_column,
    ):
        if column_name is not None:
            columns.add(column_name)
    return columns
