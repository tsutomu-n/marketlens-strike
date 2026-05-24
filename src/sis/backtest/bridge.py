from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import json

import polars as pl

from sis.backtest.costs import CostProfile, load_cost_profiles, round_trip_cost_bps
from sis.backtest.signals import ResearchSignal, load_research_signals
from sis.core.context import DecisionContext
from sis.core.decision import DecisionRecord
from sis.core.execution_plan import build_execution_plan
from sis.core.strategy import ResearchSignalStrategy
from sis.risk.risk_gate import evaluate_risk_gate


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


def _dominant_cost_source(cost_sources: list[str]) -> str | None:
    if not cost_sources:
        return None
    return max(set(cost_sources), key=cost_sources.count)


def _metrics_for_group(
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

        entry_price = _execution_price(entry)
        exit_price = _exit_price(exit_)
        if entry_price is None or exit_price is None:
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
        net = _net_return(entry_price, exit_price, "long", cost_bps)
        returns.append(net)
        cost_drag_bps += cost_bps
        cost_sources.append(cost_source)
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
    profit_factor = sum(wins) / abs(sum(losses)) if losses else (None if not wins else float("inf"))
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
        cost_source=_dominant_cost_source(cost_sources),
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
        max_drawdown=_max_drawdown(equity),
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


def _metrics_for_signals(
    quotes: pl.DataFrame,
    signals: list[ResearchSignal],
    cost_profiles: dict[tuple[str, str], CostProfile] | None = None,
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    rows_by_key: dict[tuple[str, str], list[dict]] = {}
    for row in quotes.sort("ts_client").to_dicts():
        key = (str(row["venue"]), str(row["canonical_symbol"]).upper())
        rows_by_key.setdefault(key, []).append(row)

    signals_by_symbol: dict[str, list[ResearchSignal]] = {}
    for signal in signals:
        signals_by_symbol.setdefault(signal.canonical_symbol, []).append(signal)

    metrics: list[BacktestMetrics] = []
    decision_records: list[DecisionRecord] = []
    blocked_reason_counts: dict[str, int] = {}
    executed = 0
    blocked = 0
    strategy = ResearchSignalStrategy()
    for (venue, symbol), rows in rows_by_key.items():
        symbol_signals = signals_by_symbol.get(symbol, [])
        if not symbol_signals:
            continue

        returns: list[float] = []
        equity = [1.0]
        cost_drag_bps = 0.0
        cost_sources: list[str] = []
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
            context = DecisionContext(
                decision_ts=signal.ts_signal,
                venue=venue,
                canonical_symbol=symbol,
                timeframe=signal.timeframe,
                quote_ts=_parse_quote_ts(entry["ts_client"]),
                signal_ts=signal.ts_signal,
                signal_side=signal.side,
                signal_strength=signal.signal_strength,
                strategy_name="research_signal_strategy",
                market_status=str(entry.get("market_status", "unknown")),
                is_tradable=bool(entry.get("is_tradable")),
            )
            strategy_decision = strategy.evaluate(context)
            risk_decision = evaluate_risk_gate(context, entry)
            execution_plan = build_execution_plan(context, strategy_decision, risk_decision)
            decision_records.append(
                DecisionRecord(
                    context=context,
                    strategy_decision=strategy_decision,
                    risk_decision=risk_decision,
                    execution_plan=execution_plan.model_dump(mode="json"),
                )
            )
            if not risk_decision.allowed:
                blocked += 1
                for reason in risk_decision.blocked_reasons:
                    blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
                if risk_decision.stale_rejected:
                    stale_rejected += 1
                if risk_decision.halt_rejected:
                    halt_rejected += 1
                continue

            entry_price = _execution_price(entry, signal.side)
            exit_price = _exit_price(exit_, signal.side)
            if entry_price is None or exit_price is None:
                stale_rejected += 1
                continue

            spread_raw = entry.get("spread_bps")
            spread = float(spread_raw) if isinstance(spread_raw, int | float) else None
            cost_bps, cost_source = round_trip_cost_bps(
                venue=venue,
                symbol=symbol,
                holding_horizon=signal.timeframe,
                quote_spread_bps=spread,
                cost_profiles=cost_profiles or {},
            )
            returns.append(_net_return(entry_price, exit_price, signal.side, cost_bps))
            cost_drag_bps += cost_bps
            cost_sources.append(cost_source)
            equity.append(equity[-1] * (1.0 + returns[-1]))
            executed += 1

        metrics.append(
            _metrics_from_returns(
                venue=venue,
                symbol=symbol,
                returns=returns,
                equity=equity,
                cost_drag_bps=cost_drag_bps,
                cost_source=_dominant_cost_source(cost_sources),
                stale_rejected=stale_rejected,
                halt_rejected=halt_rejected,
                candidate_count=len(symbol_signals),
            )
        )
    summary = {
        "mode": "signal_driven",
        "signals_considered": len(signals),
        "executed_count": executed,
        "blocked_count": blocked,
        "blocked_reason_counts": blocked_reason_counts,
        "records_written": len(decision_records),
    }
    return metrics, decision_records, summary


def _write_decision_records(records: list[DecisionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def _write_decision_summary(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def run_backtest_bridge_with_decisions(
    quotes_path: Path,
    signals_path: Path | None = None,
    cost_matrix_path: Path | None = None,
    decision_log_path: Path | None = None,
    decision_summary_path: Path | None = None,
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    if not quotes_path.exists():
        raise FileNotFoundError(f"Normalized quote parquet not found: {quotes_path}")
    quotes = pl.read_parquet(quotes_path)
    if quotes.is_empty():
        raise ValueError(f"Normalized quote parquet is empty: {quotes_path}")

    required = {"ts_client", "venue", "canonical_symbol", "market_status", "is_tradable"}
    missing = required.difference(quotes.columns)
    if missing:
        raise ValueError(f"Normalized quote parquet missing columns: {sorted(missing)}")

    cost_profiles = load_cost_profiles(cost_matrix_path)
    if signals_path is not None:
        signals = load_research_signals(signals_path)
        if signals:
            metrics, records, summary = _metrics_for_signals(quotes, signals, cost_profiles)
            if decision_log_path is not None:
                _write_decision_records(records, decision_log_path)
            if decision_summary_path is not None:
                _write_decision_summary(summary, decision_summary_path)
            return metrics, records, summary

    metrics = [
        _metrics_for_group(group, cost_profiles)
        for (_key, group) in quotes.group_by(["venue", "canonical_symbol"], maintain_order=True)
    ]
    summary = {
        "mode": "quote_fallback",
        "signals_considered": 0,
        "executed_count": 0,
        "blocked_count": 0,
        "blocked_reason_counts": {},
        "records_written": 0,
    }
    if decision_summary_path is not None:
        _write_decision_summary(summary, decision_summary_path)
    if decision_log_path is not None:
        _write_decision_records([], decision_log_path)
    return metrics, [], summary


def run_backtest_bridge(
    quotes_path: Path,
    signals_path: Path | None = None,
    cost_matrix_path: Path | None = None,
) -> list[BacktestMetrics]:
    metrics, _records, _summary = run_backtest_bridge_with_decisions(
        quotes_path,
        signals_path=signals_path,
        cost_matrix_path=cost_matrix_path,
    )
    return metrics


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
        "| {venue} | {symbol} | {trades} | {total:.6f} | {drawdown:.6f} | {win_rate} | {cost:.2f} | {cost_source} | {stale} | {halt} |".format(
            venue=item.venue,
            symbol=item.canonical_symbol,
            trades=item.trade_count,
            total=item.total_return,
            drawdown=item.max_drawdown,
            win_rate="" if item.win_rate is None else f"{item.win_rate:.4f}",
            cost=item.cost_drag_bps,
            cost_source=item.cost_source or "",
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
                "| Venue | Symbol | Trades | Total Return | Max Drawdown | Win Rate | Cost Drag bps | Cost Source | Stale Rejects | Halt Rejects |",
                "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
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
