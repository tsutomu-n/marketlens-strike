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


def test_market_session_window_rejects_unsupported_symbol() -> None:
    now = datetime.now(timezone.utc)

    try:
        market_session_window("trade_xyz", "BTC", now=now)
    except ValueError as exc:
        assert "Unsupported symbol" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_market_session_window_rejects_xau_as_active_trade_xyz_symbol() -> None:
    now = datetime.now(timezone.utc)

    try:
        market_session_window("trade_xyz", "XAU", now=now)
    except ValueError as exc:
        assert "Unsupported symbol" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
