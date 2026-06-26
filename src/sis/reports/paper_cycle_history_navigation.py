from __future__ import annotations

from pathlib import Path


def quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "paper_cycle_history_report": str(out_path),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
    }


def related_reports(
    out_path: Path | None, latest_phase_gate_review_report_path: str | None
) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "paper_cycle_history_report": str(out_path),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(
            reports_dir / "execution_state_comparison_history.md"
        ),
        "execution_snapshot_drift_report": str(reports_dir / "execution_snapshot_drift_history.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": latest_phase_gate_review_report_path
        or str(reports_dir / "phase_gate_review.md"),
    }
