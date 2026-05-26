from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")


def market_session(ts: datetime) -> str:
    local = ts if ts.tzinfo is not None else ts.replace(tzinfo=ZoneInfo("UTC"))
    local = local.astimezone(EASTERN)
    if local.weekday() >= 5:
        return "closed"
    t = local.time()
    if time(9, 30) <= t < time(16, 0):
        return "regular"
    if time(4, 0) <= t < time(9, 30):
        return "premarket"
    if time(16, 0) <= t < time(20, 0):
        return "afterhours"
    return "closed"


def is_regular_session(ts: datetime) -> bool:
    return market_session(ts) == "regular"
