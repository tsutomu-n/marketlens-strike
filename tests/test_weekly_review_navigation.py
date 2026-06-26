from __future__ import annotations

from pathlib import Path

from sis.reports.weekly_review_navigation import quick_navigation, related_reports


def test_quick_navigation_omits_missing_output_path() -> None:
    assert quick_navigation(None, {}) == {}


def test_quick_navigation_filters_missing_live_evidence_path() -> None:
    assert quick_navigation(
        Path("data/reports/weekly_strategy_review.md"),
        {"live_evidence_report_path": ""},
    ) == {
        "weekly_review_report": "data/reports/weekly_strategy_review.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "strategy_lifecycle_report": "data/reports/strategy_lifecycle_report.md",
    }


def test_quick_navigation_includes_live_evidence_path_when_present() -> None:
    assert (
        quick_navigation(
            Path("data/reports/weekly_strategy_review.md"),
            {"live_evidence_report_path": "data/docs/live_evidence_reports/latest.md"},
        )["live_evidence_report"]
        == "data/docs/live_evidence_reports/latest.md"
    )


def test_related_reports_omits_missing_output_path() -> None:
    assert related_reports(None, {}) == {}


def test_related_reports_uses_flat_report_paths_before_nested_report_paths() -> None:
    row = {
        "live_evidence_report_path": "data/docs/live_evidence_reports/latest.md",
        "execution_report_path": "data/reports/execution_snapshot_flat.md",
        "execution_summary": {"report_path": "data/reports/execution_snapshot_nested.md"},
        "execution_comparison_summary": {
            "report_path": "data/reports/execution_venue_comparison.md"
        },
        "execution_diagnostics_report_path": "data/reports/execution_diagnostics_flat.md",
        "execution_gap_history_summary": {"report_path": "data/reports/execution_gap_history.md"},
        "execution_state_comparison_summary": {
            "report_path": "data/reports/execution_state_comparison.md"
        },
        "execution_snapshot_drift_summary": {
            "report_path": "data/reports/execution_snapshot_drift.md"
        },
        "execution_drift_overview_summary": {
            "report_path": "data/reports/execution_drift_overview.md"
        },
    }

    assert related_reports(Path("data/reports/weekly_strategy_review.md"), row) == {
        "weekly_review_report": "data/reports/weekly_strategy_review.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "ops_review_report": "data/reports/ops_review.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "go_no_go_report": "data/research/go_no_go_report.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "strategy_lifecycle_report": "data/reports/strategy_lifecycle_report.md",
        "paper_vs_backtest_comparison_report": ("data/reports/paper_vs_backtest_comparison.md"),
        "execution_snapshot_report": "data/reports/execution_snapshot_flat.md",
        "execution_venue_comparison_report": "data/reports/execution_venue_comparison.md",
        "execution_venue_diagnostics_report": "data/reports/execution_diagnostics_flat.md",
        "execution_gap_history_report": "data/reports/execution_gap_history.md",
        "execution_state_comparison_report": "data/reports/execution_state_comparison.md",
        "execution_snapshot_drift_report": "data/reports/execution_snapshot_drift.md",
        "execution_drift_overview_report": "data/reports/execution_drift_overview.md",
        "live_evidence_report": "data/docs/live_evidence_reports/latest.md",
    }


def test_related_reports_filters_missing_nested_report_paths() -> None:
    row = {
        "execution_summary": {"report_path": ""},
        "execution_comparison_summary": {},
        "live_evidence_report_path": 123,
    }

    reports = related_reports(Path("data/reports/weekly_strategy_review.md"), row)

    assert "execution_snapshot_report" not in reports
    assert "execution_venue_comparison_report" not in reports
    assert "live_evidence_report" not in reports
