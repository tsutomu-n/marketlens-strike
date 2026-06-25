from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.backtest.engine.equity_rows import _equity_row
from sis.backtest.engine.portfolio import Portfolio


def test_equity_row_uses_mid_price_for_open_position_valuation() -> None:
    portfolio = Portfolio(
        initial_cash_usd=10_000,
        cash_usd=8_000,
        position_qty=20,
        avg_entry_price=100,
        equity=10_000,
        funding_pnl=-3.5,
    )
    row = {
        "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "mid_price": 110.0,
        "close": 105.0,
        "is_evaluation": True,
        "session_type": "regular",
        "market_status": "open",
    }

    assert _equity_row(row=row, portfolio=portfolio) == {
        "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "cash_usd": 8_000.0,
        "position_qty": 20.0,
        "equity": pytest.approx(10_200.0),
        "unrealized_pnl": pytest.approx(200.0),
        "funding_pnl": -3.5,
        "is_evaluation": True,
        "session_type": "regular",
        "market_status": "open",
    }


def test_equity_row_defaults_session_and_market_status_for_flat_portfolio() -> None:
    row = {
        "event_ts": datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        "close": None,
        "is_evaluation": False,
    }

    assert _equity_row(row=row, portfolio=Portfolio.flat(initial_cash_usd=10_000)) == {
        "event_ts": datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        "cash_usd": 10_000.0,
        "position_qty": 0.0,
        "equity": 10_000.0,
        "unrealized_pnl": 0.0,
        "funding_pnl": 0.0,
        "is_evaluation": False,
        "session_type": "unknown",
        "market_status": "unknown",
    }
