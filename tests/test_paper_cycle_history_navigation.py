from __future__ import annotations

from pathlib import Path

from sis.reports.paper_cycle_history_navigation import quick_navigation, related_reports


def test_quick_navigation_omits_missing_output_path() -> None:
    assert quick_navigation(None) == {}


def test_quick_navigation_uses_paper_cycle_report_siblings() -> None:
    out_path = Path("data/reports/paper_cycle_history.md")

    assert quick_navigation(out_path) == {
        "paper_cycle_history_report": "data/reports/paper_cycle_history.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
    }


def test_related_reports_omits_missing_output_path() -> None:
    assert related_reports(None, "data/custom/phase_gate_review.md") == {}


def test_related_reports_uses_default_phase_gate_sibling_path() -> None:
    out_path = Path("data/reports/paper_cycle_history.md")

    assert related_reports(out_path, None) == {
        "paper_cycle_history_report": "data/reports/paper_cycle_history.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "execution_gap_history_report": "data/reports/execution_gap_history.md",
        "execution_state_comparison_report": ("data/reports/execution_state_comparison_history.md"),
        "execution_snapshot_drift_report": "data/reports/execution_snapshot_drift_history.md",
        "execution_drift_overview_report": "data/reports/execution_drift_overview.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
    }


def test_related_reports_prefers_latest_phase_gate_report_path() -> None:
    out_path = Path("data/reports/paper_cycle_history.md")

    reports = related_reports(out_path, "data/archive/phase_gate_review_older.md")

    assert reports["phase_gate_review_report"] == "data/archive/phase_gate_review_older.md"
