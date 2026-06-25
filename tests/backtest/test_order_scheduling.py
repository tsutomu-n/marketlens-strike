from __future__ import annotations

from datetime import datetime, timezone

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.order import Order
from sis.backtest.engine.order_scheduling import _schedule_signal_order
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_loop import BreakoutParameters


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="order-scheduling",
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


def _row(index: int, close: float, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "_row_index": index,
        "event_ts": datetime(2026, 1, 1, index, tzinfo=timezone.utc),
        "symbol": "SP500",
        "close": close,
        "taker_fee_bps": 9.0,
        "maker_fee_bps": 3.0,
        "market_status": "open",
        "is_tradable": True,
        "block_reasons": [],
    }
    row.update(overrides)
    return row


def _open_portfolio() -> Portfolio:
    return Portfolio(
        initial_cash_usd=10_000,
        cash_usd=9_000,
        position_qty=3,
        avg_entry_price=100,
        equity=10_000,
    )


def test_schedule_signal_order_adds_entry_order_to_next_row() -> None:
    orders: list[Order] = []
    pending: dict[int, Order] = {}
    blocked: list[BlockedEvent] = []

    _schedule_signal_order(
        rows=[_row(0, 100), _row(1, 101), _row(2, 102)],
        index=1,
        breakout=BreakoutParameters(entry_lookback=1, exit_lookback=1),
        config=_config(),
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        orders=orders,
        pending_orders=pending,
        blocked=blocked,
    )

    assert blocked == []
    assert len(orders) == 1
    assert pending == {2: orders[0]}
    assert orders[0].side == "buy"
    assert orders[0].position_effect == "open"
    assert orders[0].requested_notional_usd == 1_000
    assert orders[0].signal_id == "signal-1"


def test_schedule_signal_order_adds_exit_order_to_next_row() -> None:
    orders: list[Order] = []
    pending: dict[int, Order] = {}
    blocked: list[BlockedEvent] = []

    _schedule_signal_order(
        rows=[_row(0, 100), _row(1, 99), _row(2, 98)],
        index=1,
        breakout=BreakoutParameters(entry_lookback=1, exit_lookback=1),
        config=_config(),
        portfolio=_open_portfolio(),
        orders=orders,
        pending_orders=pending,
        blocked=blocked,
    )

    assert blocked == []
    assert len(orders) == 1
    assert pending == {2: orders[0]}
    assert orders[0].side == "sell"
    assert orders[0].position_effect == "close"
    assert orders[0].requested_notional_usd == 300
    assert orders[0].requested_qty == 3
    assert orders[0].reduce_only is True
    assert orders[0].signal_id == "signal-1"


def test_schedule_signal_order_blocks_last_row_signal_without_future_fill_row() -> None:
    orders: list[Order] = []
    pending: dict[int, Order] = {}
    blocked: list[BlockedEvent] = []

    _schedule_signal_order(
        rows=[_row(7, 100), _row(8, 101)],
        index=1,
        breakout=BreakoutParameters(entry_lookback=1, exit_lookback=1),
        config=_config(),
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        orders=orders,
        pending_orders=pending,
        blocked=blocked,
    )

    assert orders == []
    assert pending == {}
    assert len(blocked) == 1
    assert blocked[0].action == "entry"
    assert blocked[0].reason == "no_future_fill_row"
    assert blocked[0].signal_id == "signal-1"
    assert blocked[0].row_index == 8


def test_schedule_signal_order_records_entry_gate_blocked_reasons() -> None:
    orders: list[Order] = []
    pending: dict[int, Order] = {}
    blocked: list[BlockedEvent] = []

    _schedule_signal_order(
        rows=[
            _row(3, 100),
            _row(
                4,
                101,
                is_tradable=False,
                block_reasons=["BLOCK_NO_BID"],
            ),
            _row(5, 102),
        ],
        index=1,
        breakout=BreakoutParameters(entry_lookback=1, exit_lookback=1),
        config=_config(),
        portfolio=Portfolio.flat(initial_cash_usd=10_000),
        orders=orders,
        pending_orders=pending,
        blocked=blocked,
    )

    assert orders == []
    assert pending == {}
    assert [event.reason for event in blocked] == [
        "is_tradable_false",
        "block_reasons_non_empty",
    ]
    assert {event.signal_id for event in blocked} == {"signal-1"}
    assert {event.row_index for event in blocked} == {4}
