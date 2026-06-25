from __future__ import annotations

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.fill import Fill
from sis.backtest.engine.forced_close import _apply_forced_end_close
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio


class BacktestError(RuntimeError):
    pass


def apply_end_position_policy(
    *,
    config: BacktestConfig,
    rows: list[dict[str, object]],
    portfolio: Portfolio,
    open_trade: dict[str, object] | None,
    orders: list[Order],
    fills: list[Fill],
    blocked: list[BlockedEvent],
    trades: list[dict[str, object]],
    equity_rows: list[dict[str, object]],
) -> tuple[Portfolio, dict[str, object] | None]:
    if config.execution.end_position_policy == "error_if_open" and portfolio.position_qty > 0:
        raise BacktestError("open position at end of run")

    if (
        config.execution.end_position_policy == "force_close_if_executable"
        and portfolio.position_qty > 0
        and rows
    ):
        return _apply_forced_end_close(
            last_row=rows[-1],
            config=config,
            portfolio=portfolio,
            open_trade=open_trade,
            orders=orders,
            fills=fills,
            blocked=blocked,
            trades=trades,
            equity_rows=equity_rows,
        )

    return portfolio, open_trade
