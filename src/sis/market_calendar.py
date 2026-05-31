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


@dataclass(frozen=True)
class MarketSessionState:
    symbol: str
    venue: str
    calendar: str | None
    ts_utc: datetime
    session_type: str
    external_session_open: bool | None
    holiday_closure: bool | None
    data_status: str
    notes: list[str]


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


def _calendar_for_symbol(venue: str, symbol: str) -> str:
    normalized_venue = venue.strip().lower()
    normalized_symbol = symbol.strip().upper()
    if normalized_venue != "trade_xyz":
        raise ValueError("Only trade_xyz is supported for market session planning.")
    if normalized_symbol in INDEX_SYMBOLS or normalized_symbol in XNYS_EQUITY_SYMBOLS:
        return "XNYS"
    raise ValueError(f"Unsupported symbol for market session planning: {normalized_symbol}")


def market_session_state(venue: str, symbol: str, ts: datetime) -> MarketSessionState:
    normalized_symbol = symbol.strip().upper()
    normalized_venue = venue.strip().lower()
    ts_utc = _ensure_tz(ts).astimezone(timezone.utc)
    try:
        calendar_name = _calendar_for_symbol(normalized_venue, normalized_symbol)
    except ValueError:
        return MarketSessionState(
            symbol=normalized_symbol,
            venue=normalized_venue,
            calendar=None,
            ts_utc=ts_utc,
            session_type="unknown",
            external_session_open=None,
            holiday_closure=None,
            data_status="unsupported_symbol",
            notes=["unsupported_symbol_for_calendar_state"],
        )

    cal = xcals.get_calendar(calendar_name)
    local_date = ts_utc.astimezone(EASTERN).date()
    day_ts = pd.Timestamp(local_date)
    if not cal.is_session(day_ts):
        return MarketSessionState(
            symbol=normalized_symbol,
            venue=normalized_venue,
            calendar=calendar_name,
            ts_utc=ts_utc,
            session_type="closed",
            external_session_open=False,
            holiday_closure=True,
            data_status="calendar_observed",
            notes=["exchange_calendar_non_session_day"],
        )

    session_open = cal.session_open(day_ts).to_pydatetime().astimezone(timezone.utc)
    session_close = cal.session_close(day_ts).to_pydatetime().astimezone(timezone.utc)
    is_open = session_open <= ts_utc < session_close
    return MarketSessionState(
        symbol=normalized_symbol,
        venue=normalized_venue,
        calendar=calendar_name,
        ts_utc=ts_utc,
        session_type="regular" if is_open else "closed",
        external_session_open=is_open,
        holiday_closure=False,
        data_status="calendar_observed",
        notes=["exchange_calendar_session_day"],
    )


def market_session_window(venue: str, symbol: str, now: datetime | None = None) -> SessionWindow:
    normalized_venue = venue.strip().lower()
    normalized_symbol = symbol.strip().upper()

    now_utc = _resolve_now(now)
    calendar = _calendar_for_symbol(normalized_venue, normalized_symbol)
    if calendar == "XNYS":
        session_open, session_close, status = _next_xnys_window(now_utc)
        recommended_start = session_open + timedelta(minutes=15)
        recommended_end = session_close - timedelta(minutes=30)
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
