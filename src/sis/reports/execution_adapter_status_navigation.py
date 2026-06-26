from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order


def execution_adapter_recommended_read_order() -> list[str]:
    return recommended_read_order(
        [
            "data/reports/execution_snapshot.md",
            "data/ops/current_state_index.json",
            "data/ops/readiness_snapshot.json",
            "data/ops/phase_gate_review_summary.json",
        ]
    )


def quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_adapter_report": str(out_path),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
    }


def related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
    }


def report_context(out_path: Path | None) -> dict[str, object]:
    return {
        "recommended_read_order": execution_adapter_recommended_read_order(),
        "quick_navigation": quick_navigation(out_path),
        "related_reports": related_reports(out_path),
    }
