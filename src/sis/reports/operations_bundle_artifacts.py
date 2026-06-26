from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order


def artifact_paths(
    *,
    monitoring_summary_path: Path | None,
    ops_review_summary_path: Path | None,
    dashboard_summary_path: Path | None,
    execution_snapshot_summary_path: Path | None,
    execution_venue_comparison_summary_path: Path | None,
    execution_venue_diagnostics_summary_path: Path | None,
    execution_gap_history_summary_path: Path | None,
    execution_state_comparison_history_summary_path: Path | None,
    execution_snapshot_drift_history_summary_path: Path | None,
    execution_drift_overview_summary_path: Path | None,
    readiness_summary_path: Path | None,
    runbook_summary_path: Path | None,
    paper_cycle_history_summary_path: Path | None,
    phase_gate_summary_path: Path | None,
) -> dict[str, str | None]:
    return {
        "monitoring_summary": str(monitoring_summary_path) if monitoring_summary_path else None,
        "ops_review_summary": str(ops_review_summary_path) if ops_review_summary_path else None,
        "dashboard_summary": str(dashboard_summary_path) if dashboard_summary_path else None,
        "execution_snapshot_summary": str(execution_snapshot_summary_path)
        if execution_snapshot_summary_path
        else None,
        "execution_venue_comparison_summary": (
            str(execution_venue_comparison_summary_path)
            if execution_venue_comparison_summary_path
            else None
        ),
        "execution_venue_diagnostics_summary": (
            str(execution_venue_diagnostics_summary_path)
            if execution_venue_diagnostics_summary_path
            else None
        ),
        "execution_gap_history_summary": (
            str(execution_gap_history_summary_path) if execution_gap_history_summary_path else None
        ),
        "execution_state_comparison_history_summary": (
            str(execution_state_comparison_history_summary_path)
            if execution_state_comparison_history_summary_path
            else None
        ),
        "execution_snapshot_drift_history_summary": (
            str(execution_snapshot_drift_history_summary_path)
            if execution_snapshot_drift_history_summary_path
            else None
        ),
        "execution_drift_overview_summary": (
            str(execution_drift_overview_summary_path)
            if execution_drift_overview_summary_path
            else None
        ),
        "readiness_summary": str(readiness_summary_path) if readiness_summary_path else None,
        "runbook_summary": str(runbook_summary_path) if runbook_summary_path else None,
        "paper_cycle_history_summary": str(paper_cycle_history_summary_path)
        if paper_cycle_history_summary_path
        else None,
        "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
    }


def recommended_read_order_items() -> list[str]:
    return recommended_read_order(
        [
            "data/ops/execution_snapshot_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
            "data/ops/execution_drift_overview_summary.json",
            "data/ops/readiness_snapshot.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
            "data/reports/operations_dashboard.md",
            "data/reports/audit_dashboard.md",
            "data/reports/operations_audit_pack.md",
            "data/reports/paper_operations_runbook.md",
        ]
    )
