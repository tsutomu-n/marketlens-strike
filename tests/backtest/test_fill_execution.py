from __future__ import annotations

from datetime import datetime, timezone

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.fill_execution import _fill_order
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="run-fill-exec",
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


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "_row_index": 7,
        "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
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


def test_fill_order_builds_open_taker_fill_from_market_like_row() -> None:
    order = Order(
        order_id="order-open",
        created_ts=datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
        symbol="SP500",
        side="buy",
        position_effect="open",
        requested_notional_usd=1_000,
        strategy_id="sp500_breakout_v0",
        signal_id="signal-7",
    )

    fill, blocked = _fill_order(
        order=order,
        row=_row(),
        config=_config(),
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
    )

    assert blocked is None
    assert fill is not None
    assert fill.fill_id == "fill-order-open"
    assert fill.side == "buy"
    assert fill.position_effect == "open"
    assert fill.qty == 10.0
    assert fill.fill_price == 100.0
    assert fill.fill_notional_usd == 1_000.0
    assert fill.fee_bps == 10.0
    assert fill.fee_amount == 1.0
    assert fill.fee_source == "row"
    assert fill.fill_price_source == "best_ask"


def test_fill_order_returns_blocked_event_when_open_fill_gate_rejects_row() -> None:
    order = Order(
        order_id="order-blocked",
        created_ts=datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
        symbol="SP500",
        side="buy",
        position_effect="open",
        requested_notional_usd=1_000,
        strategy_id="sp500_breakout_v0",
        signal_id="signal-7",
    )

    fill, blocked = _fill_order(
        order=order,
        row=_row(fill_is_tradable=False),
        config=_config(),
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
    )

    assert fill is None
    assert blocked is not None
    assert blocked.action == "open"
    assert blocked.reason == "fill_row_is_tradable_false"
    assert blocked.reason_detail == "fill_row_is_tradable_false"
    assert blocked.signal_id == "signal-7"
    assert blocked.row_index == 7
