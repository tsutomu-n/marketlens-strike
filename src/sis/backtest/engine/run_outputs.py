from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl

from sis.backtest.engine.blocked import BlockedEvent, blocked_events_to_frame
from sis.backtest.engine.fill import Fill
from sis.backtest.engine.frames import (
    equity_to_frame,
    fills_to_frame,
    orders_to_frame,
    trades_to_frame,
)
from sis.backtest.engine.metrics import calculate_metrics
from sis.backtest.engine.metrics_enrichment import enrich_run_metrics
from sis.backtest.engine.order import Order
from sis.backtest.engine.portfolio import Portfolio


@dataclass(frozen=True)
class BacktestRunOutputs:
    orders_frame: pl.DataFrame
    fills_frame: pl.DataFrame
    trades_frame: pl.DataFrame
    blocked_frame: pl.DataFrame
    equity_frame: pl.DataFrame
    metrics: dict[str, Any]


def build_run_outputs(
    *,
    initial_cash_usd: float,
    orders: list[Order],
    fills: list[Fill],
    trades: list[dict[str, object]],
    blocked: list[BlockedEvent],
    equity_rows: list[dict[str, object]],
    portfolio: Portfolio,
    end_position_policy: str | None,
    funding_events_ref: str | None,
    funding_event_count: int,
) -> BacktestRunOutputs:
    orders_frame = orders_to_frame(orders)
    fills_frame = fills_to_frame(fills)
    trades_frame = trades_to_frame(trades)
    blocked_frame = blocked_events_to_frame(blocked)
    equity_frame = equity_to_frame(equity_rows)
    metrics = calculate_metrics(
        initial_cash_usd=initial_cash_usd,
        equity_curve=equity_frame,
        trades=trades_frame,
        fills=fills_frame,
        blocked_events=blocked_frame,
        end_open_position_count=1 if portfolio.position_qty > 0 else 0,
        end_unrealized_pnl=portfolio.unrealized_pnl,
        funding_pnl=portfolio.funding_pnl,
    )
    enrich_run_metrics(
        metrics,
        position_is_open=portfolio.position_qty > 0,
        end_position_policy=end_position_policy,
        funding_events_ref=funding_events_ref,
        funding_event_count=funding_event_count,
    )
    return BacktestRunOutputs(
        orders_frame=orders_frame,
        fills_frame=fills_frame,
        trades_frame=trades_frame,
        blocked_frame=blocked_frame,
        equity_frame=equity_frame,
        metrics=metrics,
    )
