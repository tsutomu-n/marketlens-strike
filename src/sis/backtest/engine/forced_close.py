from __future__ import annotations

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.equity_rows import _equity_row
from sis.backtest.engine.fill import Fill
from sis.backtest.engine.fill_execution import _fill_order
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_loop import row_event_ts
from sis.backtest.engine.trade_lifecycle import _apply_trade_lifecycle_fill


def _apply_forced_end_close(
    *,
    last_row: dict[str, object],
    config: BacktestConfig,
    portfolio: Portfolio,
    open_trade: dict[str, object] | None,
    orders: list[Order],
    fills: list[Fill],
    blocked: list[BlockedEvent],
    trades: list[dict[str, object]],
    equity_rows: list[dict[str, object]],
) -> tuple[Portfolio, dict[str, object] | None]:
    force_order = Order(
        created_ts=row_event_ts(last_row),
        symbol=config.symbol,
        side="sell",
        position_effect="close",
        requested_notional_usd=portfolio.position_qty * portfolio.avg_entry_price,
        requested_qty=portfolio.position_qty,
        reduce_only=True,
        strategy_id=config.strategy_id,
        signal_id="forced_end_close",
    )
    orders.append(force_order)
    fill, blocked_event = _fill_order(
        order=force_order, row=last_row, config=config, portfolio=portfolio
    )
    if blocked_event is not None:
        blocked.append(blocked_event)
    if fill is not None:
        fills.append(fill)
        portfolio, open_trade, trade = _apply_trade_lifecycle_fill(
            portfolio=portfolio,
            fill=fill,
            open_trade=open_trade,
            exit_reason="forced_end_close",
        )
        if trade is not None:
            trades.append(trade)
        if equity_rows:
            equity_rows[-1] = _equity_row(row=last_row, portfolio=portfolio)
    return portfolio, open_trade
