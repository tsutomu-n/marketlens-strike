from __future__ import annotations

from typing import Any


def _reward_risk_ratio(row: dict[str, Any]) -> float | None:
    stop_loss_bps = row.get("stop_loss_bps")
    take_profit_bps = row.get("take_profit_bps")
    if stop_loss_bps is None or take_profit_bps is None:
        return None
    stop = float(stop_loss_bps)
    if stop <= 0:
        return None
    return float(take_profit_bps) / stop
