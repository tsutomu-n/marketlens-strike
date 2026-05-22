from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import polars as pl

from sis.backtest.signals import ResearchSignal, load_research_signals


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
    stale_rejected_count: int
    halt_rejected_count: int


def _parse_quote_ts(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported quote timestamp: {value!r}")


def _execution_price(row: dict, side: str = "long") -> float | None:
    if side == "short":
        for key in ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    for key in ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price"):
        value = row.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
    return None


def _exit_price(row: dict, side: str = "long") -> float | None:
    if side == "short":
        for key in ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    for key in ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price"):
        value = row.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
    return None


def _round_trip_cost_bps(row: dict) -> float:
    fee_bps = 10.0 if row.get("venue") == "gtrade" else 0.0
    spread = row.get("spread_bps")
    return fee_bps + (float(spread) if isinstance(spread, int | float) else 0.0)


def _net_return(entry_price: float, exit_price: float, side: str, cost_bps: float) -> float:
    gross = exit_price / entry_price - 1.0
    if side == "short":
        gross = entry_price / exit_price - 1.0
    return gross - cost_bps / 10_000


def _max_drawdown(equity: list[float]) -> float:
    peak = 1.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return worst


def _metrics_for_group(group: pl.DataFrame) -> BacktestMetrics:
    rows = group.sort("ts_client").to_dicts()
    venue = str(rows[0]["venue"])
    symbol = str(rows[0]["canonical_symbol"])
    returns: list[float] = []
    equity = [1.0]
    cost_drag_bps = 0.0
    stale_rejected = 0
    halt_rejected = 0
    candidate_count = max(len(rows) - 1, 0)

    for entry, exit_ in zip(rows, rows[1:], strict=False):
        if entry.get("oracle_ts_ms") is None:
            stale_rejected += 1
        if entry.get("market_status") != "open" or entry.get("is_tradable") is not True:
            halt_rejected += 1
            continue

        entry_price = _execution_price(entry)
        exit_price = _exit_price(exit_)
        if entry_price is None or exit_price is None:
            stale_rejected += 1
            continue

        cost_bps = _round_trip_cost_bps(entry)
        net = _net_return(entry_price, exit_price, "long", cost_bps)
        returns.append(net)
        cost_drag_bps += cost_bps
        equity.append(equity[-1] * (1.0 + net))

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
    profit_factor = (
        sum(wins) / abs(sum(losses))
        if losses
        else (None if not wins else float("inf"))
    )
    exposure_ratio = len(returns) / candidate_count if candidate_count else 0.0

    return BacktestMetrics(
        venue=venue,
        canonical_symbol=symbol,
        total_return=total_return,
        annual_return=None,
        max_drawdown=_max_drawdown(equity),
        sharpe=sharpe,
        win_rate=len(wins) / len(returns) if returns else None,
        profit_factor=profit_factor,
        trade_count=len(returns),
        avg_trade_return=average,
        worst_trade=min(returns) if returns else None,
        exposure_ratio=exposure_ratio,
        cost_drag_bps=cost_drag_bps,
        stale_rejected_count=stale_rejected,
        halt_rejected_count=halt_rejected,
    )


def _metrics_from_returns(
    *,
    venue: str,
    symbol: str,
    returns: list[float],
    equity: list[float],
    cost_drag_bps: float,
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
    profit_factor = (
        sum(wins) / abs(sum(losses))
        if losses
        else (None if not wins else float("inf"))
    )
    exposure_ratio = len(returns) / candidate_count if candidate_count else 0.0

    return BacktestMetrics(
        venue=venue,
        canonical_symbol=symbol,
        total_return=total_return,
        annual_return=None,
        max_drawdown=_max_drawdown(equity),
        sharpe=sharpe,
        win_rate=len(wins) / len(returns) if returns else None,
        profit_factor=profit_factor,
        trade_count=len(returns),
        avg_trade_return=average,
        worst_trade=min(returns) if returns else None,
        exposure_ratio=exposure_ratio,
        cost_drag_bps=cost_drag_bps,
        stale_rejected_count=stale_rejected,
        halt_rejected_count=halt_rejected,
    )


def _metrics_for_signals(quotes: pl.DataFrame, signals: list[ResearchSignal]) -> list[BacktestMetrics]:
    rows_by_key: dict[tuple[str, str], list[dict]] = {}
    for row in quotes.sort("ts_client").to_dicts():
        key = (str(row["venue"]), str(row["canonical_symbol"]).upper())
        rows_by_key.setdefault(key, []).append(row)

    signals_by_symbol: dict[str, list[ResearchSignal]] = {}
    for signal in signals:
        signals_by_symbol.setdefault(signal.canonical_symbol, []).append(signal)

    metrics: list[BacktestMetrics] = []
    for (venue, symbol), rows in rows_by_key.items():
        symbol_signals = signals_by_symbol.get(symbol, [])
        if not symbol_signals:
            continue

        returns: list[float] = []
        equity = [1.0]
        cost_drag_bps = 0.0
        stale_rejected = 0
        halt_rejected = 0
        quote_times = [_parse_quote_ts(row["ts_client"]) for row in rows]

        for signal in symbol_signals:
            entry_index = next(
                (index for index, quote_time in enumerate(quote_times) if quote_time >= signal.ts_signal),
                None,
            )
            if entry_index is None or entry_index + 1 >= len(rows):
                stale_rejected += 1
                continue

            entry = rows[entry_index]
            exit_ = rows[entry_index + 1]
            if entry.get("oracle_ts_ms") is None:
                stale_rejected += 1
            if entry.get("market_status") != "open" or entry.get("is_tradable") is not True:
                halt_rejected += 1
                continue

            entry_price = _execution_price(entry, signal.side)
            exit_price = _exit_price(exit_, signal.side)
            if entry_price is None or exit_price is None:
                stale_rejected += 1
                continue

            cost_bps = _round_trip_cost_bps(entry)
            returns.append(_net_return(entry_price, exit_price, signal.side, cost_bps))
            cost_drag_bps += cost_bps
            equity.append(equity[-1] * (1.0 + returns[-1]))

        metrics.append(
            _metrics_from_returns(
                venue=venue,
                symbol=symbol,
                returns=returns,
                equity=equity,
                cost_drag_bps=cost_drag_bps,
                stale_rejected=stale_rejected,
                halt_rejected=halt_rejected,
                candidate_count=len(symbol_signals),
            )
        )
    return metrics


def run_backtest_bridge(quotes_path: Path, signals_path: Path | None = None) -> list[BacktestMetrics]:
    if not quotes_path.exists():
        raise FileNotFoundError(f"Normalized quote parquet not found: {quotes_path}")
    quotes = pl.read_parquet(quotes_path)
    if quotes.is_empty():
        raise ValueError(f"Normalized quote parquet is empty: {quotes_path}")

    required = {"ts_client", "venue", "canonical_symbol", "market_status", "is_tradable"}
    missing = required.difference(quotes.columns)
    if missing:
        raise ValueError(f"Normalized quote parquet missing columns: {sorted(missing)}")

    if signals_path is not None:
        signals = load_research_signals(signals_path)
        if signals:
            return _metrics_for_signals(quotes, signals)

    return [
        _metrics_for_group(group)
        for (_key, group) in quotes.group_by(["venue", "canonical_symbol"], maintain_order=True)
    ]


def write_backtest_report(
    metrics: list[BacktestMetrics],
    out_path: Path,
    signals_path: Path | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    source = (
        f"This report uses research signals from `{signals_path}` for virtual venue execution."
        if signals_path is not None and signals_path.exists()
        else "This report uses venue quote logs for virtual execution. It is not a trading signal generator."
    )
    rows = "\n".join(
        "| {venue} | {symbol} | {trades} | {total:.6f} | {drawdown:.6f} | {win_rate} | {cost:.2f} | {stale} | {halt} |".format(
            venue=item.venue,
            symbol=item.canonical_symbol,
            trades=item.trade_count,
            total=item.total_return,
            drawdown=item.max_drawdown,
            win_rate="" if item.win_rate is None else f"{item.win_rate:.4f}",
            cost=item.cost_drag_bps,
            stale=item.stale_rejected_count,
            halt=item.halt_rejected_count,
        )
        for item in metrics
    )
    out_path.write_text(
        "\n".join(
            [
                "# Backtest Bridge Report",
                "",
                source,
                "",
                "| Venue | Symbol | Trades | Total Return | Max Drawdown | Win Rate | Cost Drag bps | Stale Rejects | Halt Rejects |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
                rows,
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_backtest_metrics_json(metrics: list[BacktestMetrics], out_path: Path) -> None:
    import json

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([asdict(item) for item in metrics], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
