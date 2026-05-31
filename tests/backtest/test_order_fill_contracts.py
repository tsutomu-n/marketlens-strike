from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sis.backtest.engine.fill import Fill
from sis.backtest.engine.order import Order


def test_order_normalizes_symbol_and_requires_reduce_only_for_close() -> None:
    order = Order(
        created_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        symbol=" sp500 ",
        side="buy",
        position_effect="open",
        requested_notional_usd=1_000,
        strategy_id="sp500_breakout_v0",
    )

    assert order.symbol == "SP500"
    assert order.order_type == "market_like"
    assert order.limit_price is None

    with pytest.raises(ValidationError, match="close orders must be reduce_only"):
        Order(
            created_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            symbol="SP500",
            side="sell",
            position_effect="close",
            requested_notional_usd=1_000,
            reduce_only=False,
            strategy_id="sp500_breakout_v0",
        )


def test_fill_requires_notional_to_match_qty_times_price_and_source() -> None:
    fill = Fill(
        fill_id="fill-001",
        order_id="order-001",
        event_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        symbol="sp500",
        side="buy",
        position_effect="open",
        qty=2,
        fill_price=100,
        fill_notional_usd=200,
        fee_bps=9,
        fee_amount=0.18,
        extra_slippage_bps=0,
        extra_slippage_amount=0,
        funding_amount_delta=0,
        liquidity_flag="taker",
        fill_price_source="best_ask",
    )

    assert fill.symbol == "SP500"
    assert fill.liquidity_flag == "taker"

    with pytest.raises(ValidationError, match="fill_notional_usd must equal qty \\* fill_price"):
        Fill(
            fill_id="fill-002",
            order_id="order-002",
            event_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            symbol="SP500",
            side="buy",
            position_effect="open",
            qty=2,
            fill_price=100,
            fill_notional_usd=199,
            fee_bps=9,
            fee_amount=0.18,
            extra_slippage_bps=0,
            extra_slippage_amount=0,
            funding_amount_delta=0,
            liquidity_flag="taker",
            fill_price_source="best_ask",
        )
