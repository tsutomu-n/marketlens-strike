from __future__ import annotations

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.fill import Fill
from sis.backtest.engine.fill_execution import _fill_order
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.trade_lifecycle import _apply_trade_lifecycle_fill


def _apply_pending_order_fill(
    *,
    order: Order,
    row: dict[str, object],
    config: BacktestConfig,
    portfolio: Portfolio,
    open_trade: dict[str, object] | None,
    fills: list[Fill],
    blocked: list[BlockedEvent],
    trades: list[dict[str, object]],
) -> tuple[Portfolio, dict[str, object] | None]:
    fill, blocked_event = _fill_order(
        order=order,
        row=row,
        config=config,
        portfolio=portfolio,
    )
    if blocked_event is not None:
        blocked.append(blocked_event)
    if fill is None:
        return portfolio, open_trade

    fills.append(fill)
    portfolio, open_trade, trade = _apply_trade_lifecycle_fill(
        portfolio=portfolio,
        fill=fill,
        open_trade=open_trade,
        exit_reason="signal_exit",
    )
    if trade is not None:
        trades.append(trade)
    return portfolio, open_trade
