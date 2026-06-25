from __future__ import annotations

from datetime import datetime, timezone

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.fill import Fill
from sis.backtest.engine.forced_close import _apply_forced_end_close
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="forced-close",
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
        "_row_index": 9,
        "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "close": 110.0,
        "best_bid": 110.0,
        "best_ask": 110.2,
        "is_evaluation": True,
        "taker_fee_bps": 10.0,
        "maker_fee_bps": 2.0,
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
        equity=9_300,
        open_entry_fees=1.0,
    )


def _open_trade() -> dict[str, object]:
    return {
        "entry_ts": datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
        "symbol": "SP500",
        "qty": 3.0,
        "entry_price": 100.0,
        "entry_fee": 1.0,
    }


def test_apply_forced_end_close_closes_position_and_replaces_last_equity_row() -> None:
    orders: list[Order] = []
    fills: list[Fill] = []
    blocked: list[BlockedEvent] = []
    trades: list[dict[str, object]] = []
    equity_rows: list[dict[str, object]] = [{"position_qty": 3.0, "equity": 9_300.0}]

    portfolio, open_trade = _apply_forced_end_close(
        last_row=_row(),
        config=_config(),
        portfolio=_open_portfolio(),
        open_trade=_open_trade(),
        orders=orders,
        fills=fills,
        blocked=blocked,
        trades=trades,
        equity_rows=equity_rows,
    )

    assert blocked == []
    assert portfolio.position_qty == 0
    assert open_trade is None
    assert len(orders) == 1
    assert orders[0].requested_notional_usd == 300
    assert orders[0].requested_qty == 3
    assert orders[0].signal_id == "forced_end_close"
    assert len(fills) == 1
    assert fills[0].fill_price == 110.0
    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "forced_end_close"
    assert equity_rows[-1]["position_qty"] == 0


def test_apply_forced_end_close_blocks_unexecutable_last_row_without_state_change() -> None:
    orders: list[Order] = []
    fills: list[Fill] = []
    blocked: list[BlockedEvent] = []
    trades: list[dict[str, object]] = []
    equity_rows: list[dict[str, object]] = [{"position_qty": 3.0, "equity": 9_300.0}]
    portfolio = _open_portfolio()
    open_trade = _open_trade()

    next_portfolio, next_open_trade = _apply_forced_end_close(
        last_row=_row(best_bid=None),
        config=_config(),
        portfolio=portfolio,
        open_trade=open_trade,
        orders=orders,
        fills=fills,
        blocked=blocked,
        trades=trades,
        equity_rows=equity_rows,
    )

    assert next_portfolio == portfolio
    assert next_open_trade == open_trade
    assert len(orders) == 1
    assert fills == []
    assert trades == []
    assert len(blocked) == 1
    assert blocked[0].action == "close"
    assert blocked[0].reason == "fill_price_unresolved"
    assert blocked[0].signal_id == "forced_end_close"
    assert equity_rows[-1] == {"position_qty": 3.0, "equity": 9_300.0}
