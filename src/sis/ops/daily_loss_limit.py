from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyLossStatus:
    allowed: bool
    current_pnl: float
    limit: float
    reason: str | None = None


def evaluate_daily_loss_limit(current_pnl: float, daily_loss_limit: float) -> DailyLossStatus:
    if current_pnl <= -abs(daily_loss_limit):
        return DailyLossStatus(
            allowed=False,
            current_pnl=current_pnl,
            limit=daily_loss_limit,
            reason="BLOCK_DAILY_LOSS_LIMIT",
        )
    return DailyLossStatus(allowed=True, current_pnl=current_pnl, limit=daily_loss_limit)


def evaluate_max_exposure(current_exposure: float, max_exposure: float) -> DailyLossStatus:
    if current_exposure > max_exposure:
        return DailyLossStatus(
            allowed=False,
            current_pnl=current_exposure,
            limit=max_exposure,
            reason="BLOCK_MAX_EXPOSURE",
        )
    return DailyLossStatus(allowed=True, current_pnl=current_exposure, limit=max_exposure)
