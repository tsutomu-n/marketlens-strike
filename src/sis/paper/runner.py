from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from sis.backtest.bridge import run_backtest_bridge_with_decisions
from sis.paper.broker import PaperBroker
from sis.core.execution_plan import ExecutionPlan
from sis.paper.fills import PaperFill, write_fills_parquet
from sis.paper.orders import PaperOrder, write_orders_parquet
from sis.paper.portfolio import PaperPortfolio, PaperPosition, write_positions_parquet
from sis.paper.report import build_daily_paper_report
from sis.state.store import StateStore


@dataclass(frozen=True)
class PaperRunSummary:
    orders_count: int
    fills_count: int
    open_positions: int
    realized_pnl: float
    orders_path: Path
    fills_path: Path
    positions_path: Path
    daily_pnl_path: Path
    report_path: Path


def _load_portfolio(store: StateStore) -> PaperPortfolio:
    payload = store.get_json("paper_positions")
    if not isinstance(payload, list):
        return PaperPortfolio()
    positions = [PaperPosition.model_validate(item) for item in payload]
    return PaperPortfolio(positions)


def _build_quote_lookup(quotes: pl.DataFrame) -> dict[tuple[str, str, str], dict]:
    lookup: dict[tuple[str, str, str], dict] = {}
    for row in quotes.to_dicts():
        ts = row["ts_client"]
        ts_key = ts.isoformat() if isinstance(ts, datetime) else str(ts)
        lookup[(str(row["venue"]), str(row["canonical_symbol"]).upper(), ts_key)] = row
    return lookup


def run_paper_step(
    data_dir: Path,
    *,
    state_path: Path,
    signals_path: Path | None = None,
    quotes_path: Path | None = None,
) -> PaperRunSummary:
    normalized_quotes_path = quotes_path or (data_dir / "normalized/quotes.parquet")
    selected_signals_path = signals_path or (data_dir / "research/signals.csv")
    decision_log_path = data_dir / "evidence/decision_logs" / f"paper_decisions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
    decision_summary_path = data_dir / "research/decision_summary.json"

    _metrics, records, _summary = run_backtest_bridge_with_decisions(
        normalized_quotes_path,
        selected_signals_path if selected_signals_path.exists() else None,
        data_dir / "research/venue_cost_matrix.csv",
        decision_log_path=decision_log_path,
        decision_summary_path=decision_summary_path,
    )
    quotes = pl.read_parquet(normalized_quotes_path)
    lookup = _build_quote_lookup(quotes)

    store = StateStore(state_path)
    portfolio = _load_portfolio(store)
    broker = PaperBroker()

    orders: list[PaperOrder] = []
    fills: list[PaperFill] = []
    realized_pnl = 0.0

    for record in records:
        execution_plan = record.execution_plan
        order = PaperOrder(
            ts_order=record.context.decision_ts,
            venue=record.context.venue,
            canonical_symbol=record.context.canonical_symbol,
            side=record.strategy_decision.side,
            action=str(execution_plan["action"]),
            quantity=1.0,
            strategy_name=record.strategy_decision.strategy_name,
            notes=list(execution_plan.get("notes", [])),
        )
        orders.append(order)
        quote = lookup.get(
            (
                record.context.venue,
                record.context.canonical_symbol,
                record.context.quote_ts.isoformat(),
            )
        )
        if quote is None:
            continue
        fill = broker.create_fill(ExecutionPlan.model_validate(execution_plan), record, quote, quantity=1.0)
        if fill is None:
            continue
        fills.append(fill)
        realized_pnl += portfolio.apply_fill(fill)

    positions = portfolio.positions()
    store.set_json("paper_positions", [position.model_dump(mode="json") for position in positions])
    store.set_json(
        "paper_last_run",
        {
            "orders_count": len(orders),
            "fills_count": len(fills),
            "open_positions": len(positions),
            "realized_pnl": realized_pnl,
        },
    )

    orders_path = write_orders_parquet(data_dir / "paper/orders.parquet", orders)
    fills_path = write_fills_parquet(data_dir / "paper/fills.parquet", fills)
    positions_path = write_positions_parquet(data_dir / "paper/positions.parquet", positions)

    daily_pnl_path = data_dir / "paper/daily_pnl.parquet"
    daily_pnl_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "realized_pnl": realized_pnl,
                "fills_count": len(fills),
                "open_positions": len(positions),
            }
        ]
    ).write_parquet(daily_pnl_path)

    report_path = data_dir / "reports/daily_paper_report.md"
    build_daily_paper_report(fills, positions, report_path)

    return PaperRunSummary(
        orders_count=len(orders),
        fills_count=len(fills),
        open_positions=len(positions),
        realized_pnl=realized_pnl,
        orders_path=orders_path,
        fills_path=fills_path,
        positions_path=positions_path,
        daily_pnl_path=daily_pnl_path,
        report_path=report_path,
    )
