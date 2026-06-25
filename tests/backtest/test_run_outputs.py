from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.fill import Fill
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_outputs import build_run_outputs


def _order() -> Order:
    return Order(
        order_id="order-1",
        created_ts=datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
        symbol="SP500",
        side="buy",
        position_effect="open",
        requested_notional_usd=1_000,
        strategy_id="sp500_breakout_v0",
        signal_id="signal-1",
    )


def _fill() -> Fill:
    return Fill(
        fill_id="fill-1",
        order_id="order-1",
        event_ts=datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
        symbol="SP500",
        side="buy",
        position_effect="open",
        qty=10,
        fill_price=100,
        fill_notional_usd=1_000,
        fee_bps=10,
        fee_amount=1,
        fee_source="row",
        extra_slippage_bps=0,
        extra_slippage_amount=0,
        funding_amount_delta=0,
        liquidity_flag="taker",
        fill_price_source="best_ask",
    )


def _blocked() -> BlockedEvent:
    return BlockedEvent(
        event_ts=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        symbol="SP500",
        action="entry",
        reason="is_tradable_false",
        strategy_id="sp500_breakout_v0",
        signal_id="signal-2",
        row_index=2,
    )


def test_build_run_outputs_preserves_frames_and_enriched_metrics() -> None:
    portfolio = Portfolio(
        initial_cash_usd=10_000,
        cash_usd=9_000,
        position_qty=10,
        avg_entry_price=100,
        unrealized_pnl=50,
        funding_pnl=-2,
        equity=10_050,
    )

    outputs = build_run_outputs(
        initial_cash_usd=10_000,
        orders=[_order()],
        fills=[_fill()],
        trades=[],
        blocked=[_blocked()],
        equity_rows=[
            {
                "event_ts": datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
                "cash_usd": 9_000.0,
                "position_qty": 10.0,
                "equity": 10_050.0,
                "unrealized_pnl": 50.0,
                "funding_pnl": -2.0,
                "is_evaluation": True,
                "session_type": "regular",
                "market_status": "open",
            }
        ],
        portfolio=portfolio,
        end_position_policy="mark_to_market_only",
        funding_events_ref="fixture://funding",
        funding_event_count=3,
    )

    assert outputs.orders_frame.height == 1
    assert outputs.fills_frame.get_column("fee_source").to_list() == ["row"]
    assert outputs.trades_frame.is_empty()
    assert outputs.blocked_frame.get_column("reason").to_list() == ["is_tradable_false"]
    assert outputs.equity_frame.get_column("session_type").to_list() == ["regular"]
    assert outputs.metrics["end_open_position_count"] == 1
    assert outputs.metrics["end_unrealized_pnl"] == 50
    assert outputs.metrics["funding_impact"] == -2
    assert outputs.metrics["open_position_at_end"] is True
    assert outputs.metrics["end_position_policy"] == "mark_to_market_only"
    assert outputs.metrics["funding_events_ref"] == "fixture://funding"
    assert outputs.metrics["funding_event_count"] == 3


def test_build_run_outputs_uses_empty_frame_schemas() -> None:
    outputs = build_run_outputs(
        initial_cash_usd=10_000,
        orders=[],
        fills=[],
        trades=[],
        blocked=[],
        equity_rows=[],
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        end_position_policy="force_close_if_executable",
        funding_events_ref=None,
        funding_event_count=0,
    )

    assert outputs.orders_frame.schema["order_id"].is_(outputs.orders_frame.schema["order_id"])
    assert "fill_price_source" in outputs.fills_frame.columns
    assert "exit_reason" in outputs.trades_frame.columns
    assert "reason" in outputs.blocked_frame.columns
    assert "equity" in outputs.equity_frame.columns
    assert outputs.metrics["net_return_after_cost"] == pytest.approx(0.0)
    assert outputs.metrics["open_position_at_end"] is False
