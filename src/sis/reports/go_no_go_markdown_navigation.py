from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


def reports_dir(out_path: Path) -> Path:
    base = out_path.parent.parent if out_path.parent.name == "research" else out_path.parent
    return base / "reports"


def quick_navigation(
    out_path: Path,
    phase_gate_summary: dict | None,
    readiness_summary: dict | None,
) -> dict[str, str]:
    report_dir = reports_dir(out_path)
    phase_gate_flat = phase_gate_flat_fields(phase_gate_summary or {})
    readiness_flat = readiness_flat_fields(readiness_summary or {})
    items = (
        ("go_no_go_report", str(out_path)),
        (
            "phase_gate_review_report",
            phase_gate_flat.get("phase_gate_review_report_path"),
        ),
        ("current_state_index_report", str(report_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(report_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(report_dir / "paper_operations_runbook.md")),
        ("live_evidence_report", readiness_flat.get("live_evidence_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def related_reports(
    out_path: Path,
    phase_gate_summary: dict | None,
    readiness_summary: dict | None,
    execution_summary: dict | None,
    execution_comparison_summary: dict | None,
    execution_diagnostics_summary: dict | None,
    execution_gap_history_summary: dict | None,
    execution_state_comparison_summary: dict | None,
    execution_snapshot_drift_summary: dict | None,
    execution_drift_overview_summary: dict | None,
) -> dict[str, str]:
    report_dir = reports_dir(out_path)
    phase_gate_flat = phase_gate_flat_fields(phase_gate_summary or {})
    readiness_flat = readiness_flat_fields(readiness_summary or {})
    execution_summary_flat = execution_snapshot_flat_fields(execution_summary or {})
    execution_comparison_flat = execution_comparison_flat_fields(execution_comparison_summary or {})
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        execution_diagnostics_summary or {}
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        execution_gap_history_summary or {}
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        execution_state_comparison_summary or {}
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_summary or {}
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        execution_drift_overview_summary or {}
    )
    items = (
        ("go_no_go_report", str(out_path)),
        ("phase_gate_review_report", phase_gate_flat.get("phase_gate_review_report_path")),
        ("current_state_index_report", str(report_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(report_dir / "readiness_snapshot.md")),
        ("operations_dashboard_report", str(report_dir / "operations_dashboard.md")),
        ("paper_operations_runbook_report", str(report_dir / "paper_operations_runbook.md")),
        ("live_evidence_report", readiness_flat.get("live_evidence_report_path")),
        ("execution_snapshot_report", execution_summary_flat.get("execution_report_path")),
        (
            "execution_venue_comparison_report",
            execution_comparison_flat.get("execution_comparison_report_path"),
        ),
        (
            "execution_venue_diagnostics_report",
            execution_diagnostics_flat.get("execution_diagnostics_report_path"),
        ),
        (
            "execution_gap_history_report",
            execution_gap_history_flat.get("execution_gap_history_report_path"),
        ),
        (
            "execution_state_comparison_report",
            execution_state_comparison_flat.get("execution_state_comparison_report_path"),
        ),
        (
            "execution_snapshot_drift_report",
            execution_snapshot_drift_flat.get("execution_snapshot_drift_report_path"),
        ),
        (
            "execution_drift_overview_report",
            execution_drift_flat.get("execution_drift_overview_report_path"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}
