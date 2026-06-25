from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_numeric_values import (
    _optional_float_from_row,
    _positive_integer_value,
    _sizing_value,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _risk_throttle_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    throttle = spec.rules.risk_throttle
    if not throttle.enabled:
        return None
    drawdown = _optional_float_from_row(row, throttle.max_drawdown_column)
    drawdown_floor = _sizing_value(
        row,
        fixed=throttle.max_drawdown_floor,
        column=throttle.max_drawdown_floor_column,
    )
    if drawdown is not None and drawdown_floor is not None and drawdown <= drawdown_floor:
        return "risk_throttle_max_drawdown"
    daily_loss = _optional_float_from_row(row, throttle.daily_loss_column)
    daily_loss_floor = _sizing_value(
        row,
        fixed=throttle.daily_loss_floor,
        column=throttle.daily_loss_floor_column,
    )
    if daily_loss is not None and daily_loss_floor is not None and daily_loss <= daily_loss_floor:
        return "risk_throttle_daily_loss"
    loss_streak = _optional_float_from_row(row, throttle.loss_streak_column)
    max_loss_streak = _positive_integer_value(
        row,
        fixed=throttle.max_loss_streak,
        column=throttle.max_loss_streak_column,
        field_name="rules.risk_throttle.max_loss_streak",
    )
    if loss_streak is not None and max_loss_streak is not None and loss_streak >= max_loss_streak:
        return "risk_throttle_loss_streak"
    return None
