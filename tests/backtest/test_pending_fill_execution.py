from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.order import Order
from sis.backtest.engine.pending_fill_execution import _apply_pending_order_fill
from sis.backtest.engine.portfolio import Portfolio


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="run-pending-fill",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )


def _row(*, hour: int = 12, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "_row_index": hour,
        "event_ts": datetime(2026, 1, 1, hour, tzinfo=timezone.utc),
        "best_ask": 100.0,
        "best_bid": 99.0,
        "taker_fee_bps": 10.0,
        "maker_fee_bps": 2.0,
        "market_status": "open",
        "is_tradable": True,
        "block_reasons": [],
    }
    row.update(overrides)
    return row


def _order(*, order_id: str, position_effect: str, signal_id: str = "signal-7") -> Order:
    return Order(
        order_id=order_id,
        created_ts=datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
        symbol="SP500",
        side="buy" if position_effect == "open" else "sell",
        position_effect=position_effect,
        requested_notional_usd=1_000,
        reduce_only=position_effect == "close",
        strategy_id="sp500_breakout_v0",
        signal_id=signal_id,
    )


def test_apply_pending_order_fill_appends_blocked_event_without_fill() -> None:
    fills = []
    blocked = []
    trades = []
    portfolio = Portfolio.flat(initial_cash_usd=10_000)

    portfolio, open_trade = _apply_pending_order_fill(
        order=_order(order_id="blocked-open", position_effect="open"),
        row=_row(fill_is_tradable=False),
        config=_config(),
        portfolio=portfolio,
        open_trade=None,
        fills=fills,
        blocked=blocked,
        trades=trades,
    )

    assert portfolio.position_qty == 0
    assert open_trade is None
    assert fills == []
    assert trades == []
    assert len(blocked) == 1
    assert blocked[0].reason == "fill_row_is_tradable_false"
    assert blocked[0].signal_id == "signal-7"


def test_apply_pending_order_fill_opens_trade_state_and_appends_fill() -> None:
    fills = []
    blocked = []
    trades = []

    portfolio, open_trade = _apply_pending_order_fill(
        order=_order(order_id="open", position_effect="open"),
        row=_row(),
        config=_config(),
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        open_trade=None,
        fills=fills,
        blocked=blocked,
        trades=trades,
    )

    assert blocked == []
    assert trades == []
    assert len(fills) == 1
    assert fills[0].fill_id == "fill-open"
    assert fills[0].position_effect == "open"
    assert portfolio.position_qty == 10.0
    assert open_trade is not None
    assert open_trade["entry_price"] == 100.0


def test_apply_pending_order_fill_closes_trade_and_records_signal_exit() -> None:
    fills = []
    blocked = []
    trades = []
    portfolio, open_trade = _apply_pending_order_fill(
        order=_order(order_id="open", position_effect="open"),
        row=_row(hour=10),
        config=_config(),
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        open_trade=None,
        fills=fills,
        blocked=blocked,
        trades=trades,
    )

    portfolio, open_trade = _apply_pending_order_fill(
        order=_order(order_id="close", position_effect="close"),
        row=_row(hour=11, best_bid=110.0),
        config=_config(),
        portfolio=portfolio,
        open_trade=open_trade,
        fills=fills,
        blocked=blocked,
        trades=trades,
    )

    assert blocked == []
    assert len(fills) == 2
    assert fills[1].fill_id == "fill-close"
    assert fills[1].position_effect == "close"
    assert portfolio.position_qty == 0
    assert open_trade is None
    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "signal_exit"
    assert trades[0]["exit_price"] == 110.0
    assert trades[0]["net_pnl"] == pytest.approx(97.9)
