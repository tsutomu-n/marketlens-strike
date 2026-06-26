from __future__ import annotations

from pathlib import Path


def quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "venue_cost_matrix_report": str(out_path),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "live_evidence_report": str(reports_dir.parent / "docs/live_evidence_reports/latest.md"),
    }


def related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "venue_cost_matrix_report": str(out_path),
        "quote_diagnostics_report": str(reports_dir / "quote_diagnostics.md"),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "go_no_go_report": str(reports_dir.parent / "research/go_no_go_report.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }
