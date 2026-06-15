from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.reporting import write_markdown_report


@dataclass(frozen=True)
class BacktestAssumptionLedgerResult:
    ledger_path: Path
    report_path: Path
    payload: dict[str, Any]


def _assumption(
    assumption_id: str,
    category: str,
    level: str,
    severity: str,
    statement: str,
    evidence: str | None,
) -> dict[str, Any]:
    return {
        "assumption_id": assumption_id,
        "category": category,
        "level": level,
        "severity": severity,
        "statement": statement,
        "evidence": evidence,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Assumption Ledger",
        "",
        f"- status: {payload['status']}",
        f"- assumption_count: {payload['summary']['assumption_count']}",
        f"- unknown_critical_count: {payload['summary']['unknown_critical_count']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Assumption | Level | Severity | Statement |",
        "|---|---|---|---|",
    ]
    for row in payload["assumptions"]:
        lines.append(
            f"| {row['assumption_id']} | {row['level']} | {row['severity']} | {row['statement']} |"
        )
    return write_markdown_report(path, lines)


def build_strategy_backtest_assumption_ledger(
    *,
    data_availability_path: Path,
    baseline_comparison_path: Path,
    no_lookahead_path: Path,
    execution_simulation_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestAssumptionLedgerResult:
    assumptions = [
        _assumption(
            "local_artifact_sources",
            "data",
            "measured" if data_availability_path.exists() else "unknown",
            "critical",
            "Backtest inputs must be local artifacts with source hashes.",
            data_availability_path.as_posix() if data_availability_path.exists() else None,
        ),
        _assumption(
            "baseline_negative_controls",
            "validation",
            "measured" if baseline_comparison_path.exists() else "unknown",
            "medium",
            "Strategy result is compared with simple baselines and negative controls.",
            baseline_comparison_path.as_posix() if baseline_comparison_path.exists() else None,
        ),
        _assumption(
            "no_lookahead_guard",
            "validation",
            "measured" if no_lookahead_path.exists() else "unknown",
            "critical",
            "No-lookahead guard artifact must exist before completion claims.",
            no_lookahead_path.as_posix() if no_lookahead_path.exists() else None,
        ),
        _assumption(
            "execution_sim_v0_boundary",
            "execution",
            "configured" if execution_simulation_path.exists() else "unknown",
            "medium",
            "Execution simulation v0 summarizes native execution-aware fields and records unsupported venue realism as assumptions.",
            execution_simulation_path.as_posix() if execution_simulation_path.exists() else None,
        ),
        _assumption(
            "market_impact_not_claimed",
            "execution",
            "configured",
            "critical",
            "Replay-style or quote-level simulation is not used as market impact proof.",
            "docs/backtest/BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md",
        ),
        _assumption(
            "live_readiness_not_claimed",
            "safety",
            "configured",
            "critical",
            "Backtest artifacts do not prove live readiness.",
            "docs/backtest/BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md",
        ),
    ]
    unknown_critical_count = sum(
        1 for row in assumptions if row["level"] == "unknown" and row["severity"] == "critical"
    )
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_assumption_ledger.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pass" if unknown_critical_count == 0 else "fail",
            "summary": {
                "assumption_count": len(assumptions),
                "unknown_critical_count": unknown_critical_count,
            },
            "assumptions": assumptions,
            "dependency_added": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "strategy_backtest_assumption_ledger.json"
    ledger_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_assumption_ledger_report.md", payload
    )
    return BacktestAssumptionLedgerResult(
        ledger_path=ledger_path, report_path=report_path, payload=payload
    )
