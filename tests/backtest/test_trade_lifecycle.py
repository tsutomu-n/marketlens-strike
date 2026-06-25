from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.backtest.engine.fill import Fill
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.trade_lifecycle import _apply_trade_lifecycle_fill


def _fill(
    *,
    side: str,
    position_effect: str,
    qty: float,
    price: float,
    fee: float,
    ts_hour: int,
    fill_id: str,
) -> Fill:
    return Fill(
        fill_id=fill_id,
        order_id=f"order-{fill_id}",
        event_ts=datetime(2026, 1, 1, ts_hour, tzinfo=timezone.utc),
        symbol="SP500",
        side=side,
        position_effect=position_effect,
        qty=qty,
        fill_price=price,
        fill_notional_usd=qty * price,
        fee_bps=10,
        fee_amount=fee,
        extra_slippage_bps=0,
        extra_slippage_amount=0,
        funding_amount_delta=0,
        liquidity_flag="taker",
        fill_price_source="best_ask" if side == "buy" else "best_bid",
    )


def test_apply_trade_lifecycle_fill_opens_trade_state_without_trade_row() -> None:
    portfolio, open_trade, trade = _apply_trade_lifecycle_fill(
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        fill=_fill(
            side="buy",
            position_effect="open",
            qty=10,
            price=100,
            fee=1,
            ts_hour=0,
            fill_id="entry",
        ),
        open_trade=None,
        exit_reason="signal_exit",
    )

    assert portfolio.position_qty == 10
    assert open_trade == {
        "entry_ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "symbol": "SP500",
        "qty": 10.0,
        "entry_price": 100.0,
        "entry_fee": 1.0,
    }
    assert trade is None


def test_apply_trade_lifecycle_fill_closes_open_trade_row() -> None:
    entry = _fill(
        side="buy",
        position_effect="open",
        qty=10,
        price=100,
        fee=1,
        ts_hour=0,
        fill_id="entry",
    )
    exit_fill = _fill(
        side="sell",
        position_effect="close",
        qty=10,
        price=110,
        fee=1.1,
        ts_hour=1,
        fill_id="exit",
    )
    portfolio, open_trade, _trade = _apply_trade_lifecycle_fill(
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        fill=entry,
        open_trade=None,
        exit_reason="signal_exit",
    )

    portfolio, open_trade, trade = _apply_trade_lifecycle_fill(
        portfolio=portfolio,
        fill=exit_fill,
        open_trade=open_trade,
        exit_reason="signal_exit",
    )

    assert portfolio.position_qty == 0
    assert open_trade is None
    assert trade is not None
    assert trade["entry_ts"] == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert trade["exit_ts"] == datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    assert trade["symbol"] == "SP500"
    assert trade["qty"] == 10.0
    assert trade["entry_price"] == 100.0
    assert trade["exit_price"] == 110.0
    assert trade["gross_pnl"] == pytest.approx(100.0)
    assert trade["net_pnl"] == pytest.approx(97.9)
    assert trade["fees_paid"] == pytest.approx(2.1)
    assert trade["exit_reason"] == "signal_exit"
