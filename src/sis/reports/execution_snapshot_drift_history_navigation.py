from __future__ import annotations

from pathlib import Path


def quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_drift_report": str(out_path),
        "execution_state_comparison_report": str(
            reports_dir / "execution_state_comparison_history.md"
        ),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
    }


def related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_drift_report": str(out_path),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(
            reports_dir / "execution_state_comparison_history.md"
        ),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }
