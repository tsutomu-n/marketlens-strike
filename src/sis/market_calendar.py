from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

EASTERN = ZoneInfo("America/New_York")
JST = ZoneInfo("Asia/Tokyo")

INDEX_SYMBOLS = {"SPY", "QQQ"}
COMMODITY_SYMBOLS = {"XAU"}


@dataclass(frozen=True)
class SessionWindow:
    symbol: str
    venue: str
    calendar: str
    now_jst: datetime
    market_status: str
    next_open_jst: datetime
    next_close_jst: datetime
    recommended_start_jst: datetime
    recommended_end_jst: datetime


def _ensure_tz(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _resolve_now(now: datetime | None) -> datetime:
    return _ensure_tz(now) if now else datetime.now(timezone.utc)


def _next_xnys_window(now_utc: datetime) -> tuple[datetime, datetime, str]:
    cal = xcals.get_calendar("XNYS")
    now_et = now_utc.astimezone(EASTERN)
    now_date = now_et.date()

    for offset in range(0, 14):
        day = now_date + timedelta(days=offset)
        day_ts = pd.Timestamp(day)
        if not cal.is_session(day_ts):
            continue

        open_et = cal.session_open(day_ts).to_pydatetime().astimezone(EASTERN)
        close_et = cal.session_close(day_ts).to_pydatetime().astimezone(EASTERN)

        if offset == 0:
            if now_et < open_et:
                return (
                    open_et.astimezone(timezone.utc),
                    close_et.astimezone(timezone.utc),
                    "PRE_OPEN",
                )
            if open_et <= now_et < close_et:
                return open_et.astimezone(timezone.utc), close_et.astimezone(timezone.utc), "OPEN"
        else:
            return open_et.astimezone(timezone.utc), close_et.astimezone(timezone.utc), "CLOSED"

    raise RuntimeError("Unable to determine next XNYS session within 14 days")


def _xau_is_market_open(now_et: datetime) -> bool:
    weekday = now_et.weekday()  # Mon=0 .. Sun=6
    t = now_et.time()

    if weekday == 5:
        return False
    if weekday == 6:
        return t >= time(18, 0)
    if weekday == 4 and t >= time(17, 0):
        return False
    return not (time(17, 0) <= t < time(18, 0))


def _next_xau_open(now_et: datetime) -> datetime:
    candidate = now_et
    for _ in range(24 * 14):
        if _xau_is_market_open(candidate):
            return candidate
        candidate += timedelta(hours=1)
        candidate = candidate.replace(minute=0, second=0, microsecond=0)
    raise RuntimeError("Unable to determine next XAU open within 14 days")


def _xau_close_for_open_time(open_et: datetime) -> datetime:
    weekday = open_et.weekday()
    if weekday == 6:
        return open_et.replace(hour=17, minute=0, second=0, microsecond=0) + timedelta(days=5)
    if weekday in {0, 1, 2, 3}:
        close = open_et.replace(hour=17, minute=0, second=0, microsecond=0)
        if open_et.time() >= time(18, 0):
            close += timedelta(days=1)
        return close
    if weekday == 4:
        return open_et.replace(hour=17, minute=0, second=0, microsecond=0)
    return open_et + timedelta(hours=1)


def _current_xau_session_open(now_et: datetime) -> datetime:
    weekday = now_et.weekday()  # Mon=0 .. Sun=6
    session_anchor = now_et.replace(hour=18, minute=0, second=0, microsecond=0)

    if weekday == 6:
        return session_anchor
    if weekday in {0, 1, 2, 3, 4}:
        if now_et.time() >= time(18, 0):
            return session_anchor
        return session_anchor - timedelta(days=1)
    raise RuntimeError("Saturday is not an open XAU session")


def _next_xau_window(now_utc: datetime) -> tuple[datetime, datetime, str]:
    now_et = now_utc.astimezone(EASTERN)
    open_now = _xau_is_market_open(now_et)
    if open_now:
        status = "OPEN"
        next_open = _current_xau_session_open(now_et)
    else:
        status = "CLOSED"
        next_open = _next_xau_open(now_et)
    next_close = _xau_close_for_open_time(next_open)
    return next_open.astimezone(timezone.utc), next_close.astimezone(timezone.utc), status


def market_session_window(venue: str, symbol: str, now: datetime | None = None) -> SessionWindow:
    normalized_venue = venue.strip().lower()
    normalized_symbol = symbol.strip().upper()
    if normalized_venue != "gtrade":
        raise ValueError("Only gtrade is supported for market session planning.")

    now_utc = _resolve_now(now)
    if normalized_symbol in INDEX_SYMBOLS:
        session_open, session_close, status = _next_xnys_window(now_utc)
        recommended_start = session_open + timedelta(minutes=15)
        recommended_end = session_close - timedelta(minutes=30)
        calendar = "XNYS"
    elif normalized_symbol in COMMODITY_SYMBOLS:
        session_open, session_close, status = _next_xau_window(now_utc)
        recommended_start = session_open + timedelta(minutes=10)
        recommended_end = session_close - timedelta(minutes=10)
        calendar = "GTRADE_COMMODITY"
    else:
        raise ValueError(f"Unsupported symbol for market session planning: {normalized_symbol}")

    return SessionWindow(
        symbol=normalized_symbol,
        venue=normalized_venue,
        calendar=calendar,
        now_jst=now_utc.astimezone(JST),
        market_status=status,
        next_open_jst=session_open.astimezone(JST),
        next_close_jst=session_close.astimezone(JST),
        recommended_start_jst=recommended_start.astimezone(JST),
        recommended_end_jst=recommended_end.astimezone(JST),
    )
