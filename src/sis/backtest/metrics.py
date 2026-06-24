from __future__ import annotations

from dataclasses import dataclass
import math

import polars as pl

from sis.backtest.costs import CostProfile, round_trip_cost_bps
from sis.backtest.prices import execution_price, exit_price, net_return


@dataclass(frozen=True)
class BacktestMetrics:
    venue: str
    canonical_symbol: str
    total_return: float
    annual_return: float | None
    max_drawdown: float
    sharpe: float | None
    win_rate: float | None
    profit_factor: float | None
    trade_count: int
    avg_trade_return: float | None
    worst_trade: float | None
    exposure_ratio: float
    cost_drag_bps: float
    cost_source: str | None
    stale_rejected_count: int
    halt_rejected_count: int


def max_drawdown(equity: list[float]) -> float:
    peak = 1.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return worst


def dominant_cost_source(cost_sources: list[str]) -> str | None:
    if not cost_sources:
        return None
    return max(set(cost_sources), key=cost_sources.count)


def metrics_for_group(
    group: pl.DataFrame,
    cost_profiles: dict[tuple[str, str], CostProfile] | None = None,
) -> BacktestMetrics:
    rows = group.sort("ts_client").to_dicts()
    venue = str(rows[0]["venue"])
    symbol = str(rows[0]["canonical_symbol"])
    returns: list[float] = []
    equity = [1.0]
    cost_drag_bps = 0.0
    cost_sources: list[str] = []
    stale_rejected = 0
    halt_rejected = 0
    candidate_count = max(len(rows) - 1, 0)

    for entry, exit_ in zip(rows, rows[1:], strict=False):
        if entry.get("oracle_ts_ms") is None:
            stale_rejected += 1
        if entry.get("market_status") != "open" or entry.get("is_tradable") is not True:
            halt_rejected += 1
            continue

        entry_price = execution_price(entry)
        exit_price_value = exit_price(exit_)
        if entry_price is None or exit_price_value is None:
            stale_rejected += 1
            continue

        spread_raw = entry.get("spread_bps")
        spread = float(spread_raw) if isinstance(spread_raw, int | float) else None
        cost_bps, cost_source = round_trip_cost_bps(
            venue=venue,
            symbol=symbol,
            holding_horizon="4h",
            quote_spread_bps=spread,
            cost_profiles=cost_profiles or {},
        )
        net = net_return(entry_price, exit_price_value, "long", cost_bps)
        returns.append(net)
        cost_drag_bps += cost_bps
        cost_sources.append(cost_source)
        equity.append(equity[-1] * (1.0 + net))

    return metrics_from_returns(
        venue=venue,
        symbol=symbol,
        returns=returns,
        equity=equity,
        cost_drag_bps=cost_drag_bps,
        cost_source=dominant_cost_source(cost_sources),
        stale_rejected=stale_rejected,
        halt_rejected=halt_rejected,
        candidate_count=candidate_count,
    )


def metrics_from_returns(
    *,
    venue: str,
    symbol: str,
    returns: list[float],
    equity: list[float],
    cost_drag_bps: float,
    cost_source: str | None,
    stale_rejected: int,
    halt_rejected: int,
    candidate_count: int,
) -> BacktestMetrics:
    total_return = equity[-1] - 1.0
    average = sum(returns) / len(returns) if returns else None
    variance = (
        sum((item - average) ** 2 for item in returns) / len(returns)
        if returns and average is not None
        else None
    )
    sharpe = (
        average / math.sqrt(variance) * math.sqrt(252)
        if average is not None and variance and variance > 0
        else None
    )
    wins = [item for item in returns if item > 0]
    losses = [item for item in returns if item < 0]
    profit_factor = sum(wins) / abs(sum(losses)) if losses else (None if not wins else float("inf"))
    exposure_ratio = len(returns) / candidate_count if candidate_count else 0.0

    return BacktestMetrics(
        venue=venue,
        canonical_symbol=symbol,
        total_return=total_return,
        annual_return=None,
        max_drawdown=max_drawdown(equity),
        sharpe=sharpe,
        win_rate=len(wins) / len(returns) if returns else None,
        profit_factor=profit_factor,
        trade_count=len(returns),
        avg_trade_return=average,
        worst_trade=min(returns) if returns else None,
        exposure_ratio=exposure_ratio,
        cost_drag_bps=cost_drag_bps,
        cost_source=cost_source,
        stale_rejected_count=stale_rejected,
        halt_rejected_count=halt_rejected,
    )
