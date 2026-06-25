from __future__ import annotations

from dataclasses import dataclass, field

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.fill import Fill
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio


@dataclass
class BacktestRunState:
    portfolio: Portfolio
    orders: list[Order] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    blocked: list[BlockedEvent] = field(default_factory=list)
    equity_rows: list[dict[str, object]] = field(default_factory=list)
    trades: list[dict[str, object]] = field(default_factory=list)
    pending_orders: dict[int, Order] = field(default_factory=dict)
    open_trade: dict[str, object] | None = None
    recorded_warnings: set[str] = field(default_factory=set)
    next_funding_event_index: int = 0


def initialize_backtest_run_state(*, initial_cash_usd: float) -> BacktestRunState:
    return BacktestRunState(portfolio=Portfolio.flat(initial_cash_usd=initial_cash_usd))
