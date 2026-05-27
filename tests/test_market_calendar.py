from datetime import datetime, timedelta, timezone

from sis.market_calendar import market_session_window


def test_market_session_window_for_qqq_uses_xnys_and_recommended_offsets() -> None:
    now = datetime.fromisoformat("2026-05-22T12:00:00+00:00")

    window = market_session_window("trade_xyz", "QQQ", now=now)

    assert window.symbol == "QQQ"
    assert window.calendar == "XNYS"
    assert window.next_open_jst < window.next_close_jst
    assert window.recommended_start_jst == window.next_open_jst + timedelta(minutes=15)
    assert window.recommended_end_jst == window.next_close_jst - timedelta(minutes=30)


def test_market_session_window_for_xau_uses_commodity_config() -> None:
    now = datetime.fromisoformat("2026-05-22T14:01:00+00:00")

    window = market_session_window("trade_xyz", "XAU", now=now)

    assert window.symbol == "XAU"
    assert window.calendar == "TRADE_XYZ_COMMODITY"
    assert window.next_open_jst < window.next_close_jst
    assert window.next_open_jst.isoformat() == "2026-05-22T07:00:00+09:00"
    assert window.recommended_start_jst == window.next_open_jst + timedelta(minutes=10)
    assert window.recommended_end_jst == window.next_close_jst - timedelta(minutes=10)


def test_xau_reopen_after_daily_break_closes_next_day() -> None:
    now = datetime.fromisoformat("2026-05-25T21:30:00+00:00")  # Mon 17:30 ET

    window = market_session_window("trade_xyz", "XAU", now=now)

    assert window.next_close_jst > window.next_open_jst
    assert window.next_open_jst.isoformat() == "2026-05-26T07:00:00+09:00"
    assert window.next_close_jst.isoformat() == "2026-05-27T06:00:00+09:00"


def test_xau_open_session_uses_session_anchor_for_recommended_start() -> None:
    now = datetime.fromisoformat("2026-05-22T14:01:00+00:00")  # Thu 10:01 ET

    window = market_session_window("trade_xyz", "XAU", now=now)

    assert window.next_open_jst.isoformat() == "2026-05-22T07:00:00+09:00"
    assert window.recommended_start_jst.isoformat() == "2026-05-22T07:10:00+09:00"
    assert window.next_close_jst.isoformat() == "2026-05-23T06:00:00+09:00"


def test_market_session_window_rejects_unsupported_symbol() -> None:
    now = datetime.now(timezone.utc)

    try:
        market_session_window("trade_xyz", "BTC", now=now)
    except ValueError as exc:
        assert "Unsupported symbol" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
