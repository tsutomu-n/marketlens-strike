from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

EASTERN = ZoneInfo("America/New_York")
JST = ZoneInfo("Asia/Tokyo")

INDEX_SYMBOLS = {"SPY", "QQQ", "SP500", "XYZ100"}
XNYS_EQUITY_SYMBOLS = {"NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AMD", "EWJ"}


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


def market_session_window(venue: str, symbol: str, now: datetime | None = None) -> SessionWindow:
    normalized_venue = venue.strip().lower()
    normalized_symbol = symbol.strip().upper()
    if normalized_venue != "trade_xyz":
        raise ValueError("Only trade_xyz is supported for market session planning.")

    now_utc = _resolve_now(now)
    if normalized_symbol in INDEX_SYMBOLS or normalized_symbol in XNYS_EQUITY_SYMBOLS:
        session_open, session_close, status = _next_xnys_window(now_utc)
        recommended_start = session_open + timedelta(minutes=15)
        recommended_end = session_close - timedelta(minutes=30)
        calendar = "XNYS"
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
