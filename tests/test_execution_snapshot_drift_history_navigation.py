from __future__ import annotations

from pathlib import Path

from sis.reports.execution_snapshot_drift_history_navigation import (
    quick_navigation,
    related_reports,
)


def test_quick_navigation_omits_missing_output_path() -> None:
    assert quick_navigation(None) == {}


def test_quick_navigation_preserves_exact_order_and_report_paths() -> None:
    out_path = Path("data/reports/execution_snapshot_drift_history.md")

    assert quick_navigation(out_path) == {
        "execution_snapshot_drift_report": "data/reports/execution_snapshot_drift_history.md",
        "execution_state_comparison_report": ("data/reports/execution_state_comparison_history.md"),
        "execution_gap_history_report": "data/reports/execution_gap_history.md",
        "execution_drift_overview_report": "data/reports/execution_drift_overview.md",
        "current_state_index_report": "data/reports/current_state_index.md",
    }


def test_related_reports_omits_missing_output_path() -> None:
    assert related_reports(None) == {}


def test_related_reports_preserves_exact_order_and_report_paths() -> None:
    out_path = Path("data/reports/execution_snapshot_drift_history.md")

    assert related_reports(out_path) == {
        "execution_snapshot_drift_report": "data/reports/execution_snapshot_drift_history.md",
        "execution_snapshot_report": "data/reports/execution_snapshot.md",
        "execution_venue_comparison_report": "data/reports/execution_venue_comparison.md",
        "execution_venue_diagnostics_report": "data/reports/execution_venue_diagnostics.md",
        "execution_gap_history_report": "data/reports/execution_gap_history.md",
        "execution_state_comparison_report": ("data/reports/execution_state_comparison_history.md"),
        "execution_drift_overview_report": "data/reports/execution_drift_overview.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
    }
