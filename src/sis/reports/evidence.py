from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sis.reports.go_no_go import build_go_no_go_report
from sis.reports.summary_normalizers import (
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_lineage_fields_from_payload,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_state_comparison_summary,
    phase_gate_flat_fields,
    normalize_phase_gate_summary,
    readiness_flat_fields,
    normalize_readiness_summary,
)
from sis.storage.jsonl_store import write_json
from sis.venues.ostium.positions import latest_positions_sidecar


def _reports_dir(data_dir: Path) -> Path:
    return data_dir / "reports"


def _quick_navigation(
    data_dir: Path,
    phase_gate_summary: dict[str, object],
    readiness_summary: dict[str, object],
) -> dict[str, str]:
    reports_dir = _reports_dir(data_dir)
    items: list[tuple[str, str | None]] = [
        ("evidence_card_report", None),
        (
            "go_no_go_report",
            str(data_dir / "research/go_no_go_report.md"),
        ),
        (
            "phase_gate_review_report",
            phase_gate_summary.get("phase_gate_review_report_path")
            if isinstance(phase_gate_summary.get("phase_gate_review_report_path"), str)
            else str(reports_dir / "phase_gate_review.md"),
        ),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("remediation_scoreboard_report", str(reports_dir / "remediation_scoreboard.md")),
        (
            "live_evidence_report",
            readiness_summary.get("live_evidence_report_path")
            if isinstance(readiness_summary.get("live_evidence_report_path"), str)
            else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(
    data_dir: Path,
    phase_gate_summary: dict[str, object],
    readiness_summary: dict[str, object],
    execution_summary: dict[str, object],
    execution_comparison_summary: dict[str, object],
    execution_diagnostics_summary: dict[str, object],
    execution_gap_history_summary: dict[str, object],
    execution_state_comparison_summary: dict[str, object],
    execution_snapshot_drift_summary: dict[str, object],
    execution_drift_overview_summary: dict[str, object],
) -> dict[str, str]:
    reports_dir = _reports_dir(data_dir)
    items: list[tuple[str, str | None]] = [
        ("go_no_go_report", str(data_dir / "research/go_no_go_report.md")),
        (
            "phase_gate_review_report",
            phase_gate_summary.get("phase_gate_review_report_path")
            if isinstance(phase_gate_summary.get("phase_gate_review_report_path"), str)
            else str(reports_dir / "phase_gate_review.md"),
        ),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("ops_review_report", str(reports_dir / "ops_review.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("paper_vs_backtest_comparison_report", str(reports_dir / "paper_vs_backtest_comparison.md")),
        ("remediation_scoreboard_report", str(reports_dir / "remediation_scoreboard.md")),
        (
            "live_evidence_report",
            readiness_summary.get("live_evidence_report_path")
            if isinstance(readiness_summary.get("live_evidence_report_path"), str)
            else None,
        ),
        (
            "execution_snapshot_report",
            execution_summary.get("report_path")
            if isinstance(execution_summary.get("report_path"), str)
            else None,
        ),
        (
            "execution_venue_comparison_report",
            execution_comparison_summary.get("report_path")
            if isinstance(execution_comparison_summary.get("report_path"), str)
            else None,
        ),
        (
            "execution_venue_diagnostics_report",
            execution_diagnostics_summary.get("report_path")
            if isinstance(execution_diagnostics_summary.get("report_path"), str)
            else None,
        ),
        (
            "execution_gap_history_report",
            execution_gap_history_summary.get("report_path")
            if isinstance(execution_gap_history_summary.get("report_path"), str)
            else None,
        ),
        (
            "execution_state_comparison_report",
            execution_state_comparison_summary.get("report_path")
            if isinstance(execution_state_comparison_summary.get("report_path"), str)
            else None,
        ),
        (
            "execution_snapshot_drift_report",
            execution_snapshot_drift_summary.get("report_path")
            if isinstance(execution_snapshot_drift_summary.get("report_path"), str)
            else None,
        ),
        (
            "execution_drift_overview_report",
            execution_drift_overview_summary.get("report_path")
            if isinstance(execution_drift_overview_summary.get("report_path"), str)
            else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sha256_tree(root: Path) -> str | None:
    if not root.exists():
        return None
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        return None
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def build_evidence_card(
    data_dir: Path,
    out_dir: Path,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
) -> Path:
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S")
    report = build_go_no_go_report(data_dir)
    ostium_positions = latest_positions_sidecar(data_dir / "raw/sidecar/ostium")
    normalized_phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    latest_execution_lineage = latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary=timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(
            timeline_latest_execution_comparison_summary
        ),
        bundle_history_latest_execution_summary=(
            bundle_history_latest_execution_summary
        ),
        bundle_history_latest_execution_comparison_summary=(
            bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=cycle_history_latest_execution_summary,
        cycle_history_latest_execution_comparison_summary=(
            cycle_history_latest_execution_comparison_summary
        ),
    )
    normalized_execution_summary = normalize_execution_snapshot_summary(execution_summary)
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary
    )
    normalized_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        execution_diagnostics_summary
    )
    normalized_execution_gap_history_summary = normalize_execution_gap_history_summary(
        execution_gap_history_summary
    )
    normalized_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        execution_state_comparison_summary
    )
    normalized_execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
        execution_snapshot_drift_summary
    )
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    phase_gate_flat = phase_gate_flat_fields(normalized_phase_gate_summary)
    readiness_flat = readiness_flat_fields(normalized_readiness_summary)
    execution_flat = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        normalized_execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        normalized_execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        normalized_execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        normalized_execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    card = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "scope": {
            "venues": ["gtrade", "ostium"],
            "symbols": ["SPY", "QQQ", "XAU"],
            "timeframes": ["4h", "1d", "3d"],
            "scalping_policy": "prohibited_by_default",
        },
        "data": {
            "raw_quote_digest": sha256_tree(data_dir / "raw/quotes"),
            "gtrade_registry_digest": sha256_file(data_dir / "registry/gtrade_instrument_registry.json"),
            "ostium_registry_digest": sha256_file(data_dir / "registry/ostium_instrument_registry.json"),
            "ostium_positions_digest": sha256_file(ostium_positions) if ostium_positions else None,
            "normalized_quote_digest": sha256_file(data_dir / "normalized/quotes.parquet"),
            "cost_matrix_digest": sha256_file(data_dir / "research/venue_cost_matrix.csv"),
            "research_signals_digest": sha256_file(data_dir / "research/signals.csv"),
            "backtest_report_digest": sha256_file(data_dir / "research/backtest_report.md"),
            "decision_summary_digest": sha256_file(data_dir / "research/decision_summary.json"),
            "go_no_go_report_digest": sha256_file(data_dir / "research/go_no_go_report.md"),
            "decision_logs_digest": sha256_tree(data_dir / "evidence/decision_logs"),
        },
        "decision": report.decision.value,
        "venue_decisions": [item.model_dump(mode="json") for item in report.venue_decisions],
        "criteria": [item.model_dump(mode="json") for item in report.criteria],
        "blockers": report.blockers,
        "next_actions": report.next_actions,
        "audit_summary": audit_summary if isinstance(audit_summary, dict) else {},
        "phase_gate_summary": normalized_phase_gate_summary,
        **phase_gate_flat,
        "readiness_summary": normalized_readiness_summary,
        **readiness_flat,
        **latest_execution_lineage,
        "execution_summary": normalized_execution_summary,
        **execution_flat,
        "execution_comparison_summary": normalized_execution_comparison_summary,
        **execution_comparison_flat,
        "execution_diagnostics_summary": normalized_execution_diagnostics_summary,
        **execution_diagnostics_flat,
        "execution_gap_history_summary": normalized_execution_gap_history_summary,
        **execution_gap_history_flat,
        "execution_state_comparison_summary": normalized_execution_state_comparison_summary,
        **execution_state_comparison_flat,
        "execution_snapshot_drift_summary": normalized_execution_snapshot_drift_summary,
        **execution_snapshot_drift_flat,
        "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
        **execution_drift_flat,
    }
    out_path = out_dir / f"evidence_card_{run_id}.json"
    card["quick_navigation"] = {
        **_quick_navigation(data_dir, normalized_phase_gate_summary, normalized_readiness_summary),
        "evidence_card_report": str(out_path),
    }
    card["related_reports"] = _related_reports(
        data_dir,
        normalized_phase_gate_summary,
        normalized_readiness_summary,
        normalized_execution_summary,
        normalized_execution_comparison_summary,
        normalized_execution_diagnostics_summary,
        normalized_execution_gap_history_summary,
        normalized_execution_state_comparison_summary,
        normalized_execution_snapshot_drift_summary,
        normalized_execution_drift_overview_summary,
    )
    write_json(out_path, card)
    return out_path
