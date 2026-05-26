from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import polars as pl
import yaml

from sis.backtest.bridge import run_backtest_bridge_with_decisions
from sis.paper.broker import PaperBroker
from sis.core.execution_plan import ExecutionPlan
from sis.paper.fills import PaperFill, write_fills_parquet
from sis.paper.orders import PaperOrder, write_orders_parquet
from sis.paper.portfolio import PaperPortfolio, PaperPosition, write_positions_parquet
from sis.paper.report import build_daily_paper_report
from sis.risk.halt_policy import load_halt_policy
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    merged_latest_execution_payload_and_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.state.store import StateStore
from sis.storage.jsonl_store import read_json


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


def _read_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _read_normalized_summary(
    *,
    data_dir: Path,
    summary_path: Path,
    report_path: str | None,
    normalizer: Callable[[dict], dict],
) -> dict:
    payload = _read_json_dict(summary_path)
    if report_path is not None:
        payload = {
            **payload,
            "report_path": str(data_dir / report_path),
        }
    return normalizer(payload)


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


def _read_audit_summary(data_dir: Path) -> dict:
    audit_dashboard_path = data_dir / "ops/audit_dashboard_summary.json"
    audit_bundle_path = data_dir / "ops/audit_bundle_manifest.json"
    audit_dashboard = _read_json_dict(audit_dashboard_path)
    audit_bundle = _read_json_dict(audit_bundle_path)
    return audit_summary_fields(audit_dashboard, audit_bundle)


def _read_audit_dashboard_summary(data_dir: Path) -> dict:
    audit_dashboard_path = data_dir / "ops/audit_dashboard_summary.json"
    return _read_json_dict(audit_dashboard_path)


def _read_audit_bundle_summary(data_dir: Path) -> dict:
    audit_bundle_path = data_dir / "ops/audit_bundle_manifest.json"
    return _read_json_dict(audit_bundle_path)


def _read_operations_bundle_manifest(data_dir: Path) -> dict:
    bundle_path = data_dir / "ops/operations_bundle_manifest.json"
    return _read_json_dict(bundle_path)


def _read_phase_gate_summary(data_dir: Path) -> dict:
    phase_gate_path = data_dir / "ops/phase_gate_review_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=phase_gate_path,
        report_path=None,
        normalizer=normalize_phase_gate_summary,
    )


def _read_execution_drift_overview_summary(data_dir: Path) -> dict:
    overview_path = data_dir / "ops/execution_drift_overview_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=overview_path,
        report_path="reports/execution_drift_overview.md",
        normalizer=normalize_execution_drift_overview_summary,
    )


def _read_execution_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_snapshot_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_snapshot.md",
        normalizer=normalize_execution_snapshot_summary,
    )


def _read_execution_comparison_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_venue_comparison_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_venue_comparison.md",
        normalizer=normalize_execution_comparison_summary,
    )


def _read_execution_diagnostics_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_venue_diagnostics_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_venue_diagnostics.md",
        normalizer=normalize_execution_diagnostics_summary,
    )


def _read_execution_gap_history_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_gap_history_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_gap_history.md",
        normalizer=normalize_execution_gap_history_summary,
    )


def _read_execution_state_comparison_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_state_comparison_history_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_state_comparison_history.md",
        normalizer=normalize_execution_state_comparison_summary,
    )


def _read_execution_snapshot_drift_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_snapshot_drift_history_summary.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_snapshot_drift_history.md",
        normalizer=normalize_execution_snapshot_drift_summary,
    )


def _read_readiness_summary(data_dir: Path) -> dict:
    readiness_path = data_dir / "ops/readiness_snapshot.json"
    return _read_normalized_summary(
        data_dir=data_dir,
        summary_path=readiness_path,
        report_path=None,
        normalizer=normalize_readiness_summary,
    )


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
    halt_policy = load_halt_policy(Path("configs/halt_policy.yaml"))
    fee_model_path = Path("configs/fee_model.trade_xyz.yaml")
    if fee_model_path.exists():
        loaded_fee_model = yaml.safe_load(fee_model_path.read_text(encoding="utf-8"))
        fee_model = loaded_fee_model if isinstance(loaded_fee_model, dict) else {}
    else:
        fee_model = {}
    broker = PaperBroker(halt_policy=halt_policy, fee_model=fee_model)

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
    audit_dashboard_summary = _read_audit_dashboard_summary(data_dir)
    audit_bundle_summary = _read_audit_bundle_summary(data_dir)
    operations_bundle_manifest = _read_operations_bundle_manifest(data_dir)
    audit_summary = _read_audit_summary(data_dir)
    phase_gate_summary = normalize_phase_gate_summary(_read_phase_gate_summary(data_dir))
    execution_drift_overview_summary = _read_execution_drift_overview_summary(data_dir)
    execution_summary = _read_execution_summary(data_dir)
    execution_comparison_summary = _read_execution_comparison_summary(data_dir)
    execution_diagnostics_summary = _read_execution_diagnostics_summary(data_dir)
    execution_gap_history_summary = _read_execution_gap_history_summary(data_dir)
    execution_state_comparison_summary = _read_execution_state_comparison_summary(data_dir)
    execution_snapshot_drift_summary = _read_execution_snapshot_drift_summary(data_dir)
    readiness_summary = _read_readiness_summary(data_dir)
    phase_gate_fields = phase_gate_flat_fields(phase_gate_summary)
    readiness_fields = readiness_flat_fields(readiness_summary)
    execution_summary_fields = execution_snapshot_flat_fields(execution_summary)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison_summary)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics_summary)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history_summary)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison_summary
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_summary
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview_summary)
    latest_execution_payload, latest_execution_lineage = (
        merged_latest_execution_payload_and_fields(
            audit_dashboard_summary,
            audit_bundle_summary,
            operations_bundle_manifest,
        )
    )
    store.set_json(
        "paper_last_run",
        {
            "orders_count": len(orders),
            "fills_count": len(fills),
            "open_positions": len(positions),
            "realized_pnl": realized_pnl,
            "audit": audit_summary,
            "audit_summary": audit_summary,
            **latest_execution_lineage,
            "phase_gate": phase_gate_summary,
            "phase_gate_summary": phase_gate_summary,
            **phase_gate_fields,
            "readiness_summary": readiness_summary,
            **readiness_fields,
            "execution_summary": execution_summary,
            **execution_summary_fields,
            "execution_comparison_summary": execution_comparison_summary,
            **execution_comparison_fields,
            "execution_diagnostics_summary": execution_diagnostics_summary,
            **execution_diagnostics_fields,
            "execution_gap_history_summary": execution_gap_history_summary,
            **execution_gap_history_fields,
            "execution_state_comparison_summary": execution_state_comparison_summary,
            **execution_state_comparison_fields,
            "execution_snapshot_drift_summary": execution_snapshot_drift_summary,
            **execution_snapshot_drift_fields,
            "execution_drift_overview_summary": execution_drift_overview_summary,
            **execution_drift_fields,
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
    build_daily_paper_report(
        fills,
        positions,
        report_path,
        audit_summary=audit_summary,
        phase_gate_summary=phase_gate_summary,
        readiness_summary=readiness_summary,
        **latest_execution_payload,
        execution_gap_history_summary=execution_gap_history_summary,
        execution_state_comparison_summary=execution_state_comparison_summary,
        execution_snapshot_drift_summary=execution_snapshot_drift_summary,
        execution_drift_overview_summary=execution_drift_overview_summary,
    )

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
