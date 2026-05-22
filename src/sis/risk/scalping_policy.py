from __future__ import annotations

from dataclasses import dataclass


PROHIBITED_TIMEFRAMES = {"1s", "5s", "15s", "1m", "5m"}
PREFERRED_TIMEFRAMES = {"4h", "1d", "3d"}
MINIMUM_ALLOWED_TIMEFRAME = "30m"


@dataclass(frozen=True)
class ScalpingDecision:
    allowed: bool
    reason: str


def check_timeframe(timeframe: str) -> ScalpingDecision:
    normalized = timeframe.strip().lower()
    if normalized in PROHIBITED_TIMEFRAMES:
        return ScalpingDecision(False, "BLOCK_SCALPING_TIMEFRAME")
    if normalized in PREFERRED_TIMEFRAMES or normalized == MINIMUM_ALLOWED_TIMEFRAME:
        return ScalpingDecision(True, "ALLOW_TIMEFRAME")
    return ScalpingDecision(False, "BLOCK_UNKNOWN_TIMEFRAME")

