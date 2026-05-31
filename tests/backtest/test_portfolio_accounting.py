from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.backtest.engine.fill import Fill
from sis.backtest.engine.portfolio import Portfolio


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


def test_long_only_portfolio_round_trip_realizes_net_pnl_and_returns_flat() -> None:
    portfolio = Portfolio.flat(initial_cash_usd=10_000)

    entry = _fill(
        side="buy",
        position_effect="open",
        qty=10,
        price=100,
        fee=1.0,
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

    after_entry = portfolio.apply_fill(entry)
    after_exit = after_entry.apply_fill(exit_fill)

    assert after_entry.position_qty == 10
    assert after_entry.avg_entry_price == 100
    assert after_entry.cash_usd == pytest.approx(8_999.0)
    assert after_entry.fees_paid == pytest.approx(1.0)

    assert after_exit.position_qty == 0
    assert after_exit.avg_entry_price == 0
    assert after_exit.cash_usd == pytest.approx(10_097.9)
    assert after_exit.realized_pnl == pytest.approx(97.9)
    assert after_exit.unrealized_pnl == 0
    assert after_exit.fees_paid == pytest.approx(2.1)
    assert after_exit.equity == pytest.approx(10_097.9)


def test_long_only_portfolio_rejects_sell_open() -> None:
    portfolio = Portfolio.flat(initial_cash_usd=10_000)
    sell_open = _fill(
        side="sell",
        position_effect="open",
        qty=1,
        price=100,
        fee=0,
        ts_hour=0,
        fill_id="sell-open",
    )

    with pytest.raises(ValueError, match="long-only portfolio only supports buy/open fills"):
        portfolio.apply_fill(sell_open)


def test_long_only_portfolio_rejects_close_larger_than_position() -> None:
    portfolio = Portfolio.flat(initial_cash_usd=10_000).apply_fill(
        _fill(
            side="buy",
            position_effect="open",
            qty=1,
            price=100,
            fee=0,
            ts_hour=0,
            fill_id="entry",
        )
    )

    with pytest.raises(ValueError, match="close quantity exceeds open position"):
        portfolio.apply_fill(
            _fill(
                side="sell",
                position_effect="close",
                qty=2,
                price=110,
                fee=0,
                ts_hour=1,
                fill_id="exit",
            )
        )
