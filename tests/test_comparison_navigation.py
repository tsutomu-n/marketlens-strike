from pathlib import Path

from sis.reports.comparison_navigation import (
    dict_or_empty,
    quick_navigation,
    related_reports,
)


def test_dict_or_empty_returns_dict_or_empty() -> None:
    value = {"a": 1}

    assert dict_or_empty(value) == value
    assert dict_or_empty([("a", 1)]) == {}


def test_quick_navigation_omits_missing_output_path() -> None:
    assert quick_navigation(None, "data/reports/phase_gate_review.md") == {}


def test_quick_navigation_filters_missing_phase_gate_report() -> None:
    out_path = Path("data/reports/paper_vs_backtest_comparison.md")

    assert quick_navigation(out_path, None) == {
        "paper_vs_backtest_comparison_report": ("data/reports/paper_vs_backtest_comparison.md"),
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
    }


def test_quick_navigation_includes_phase_gate_report_in_expected_order() -> None:
    out_path = Path("data/reports/paper_vs_backtest_comparison.md")

    assert quick_navigation(out_path, "data/reports/phase_gate_review.md") == {
        "paper_vs_backtest_comparison_report": ("data/reports/paper_vs_backtest_comparison.md"),
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
    }


def test_related_reports_omits_missing_output_path() -> None:
    assert related_reports(None, {}) == {}


def test_related_reports_includes_nested_execution_report_paths() -> None:
    out_path = Path("data/reports/paper_vs_backtest_comparison.md")

    assert related_reports(
        out_path,
        {
            "phase_gate": {
                "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            },
            "execution_summary": {
                "execution_report_path": "data/reports/execution_snapshot.md",
            },
            "execution_comparison_summary": {
                "execution_comparison_report_path": ("data/reports/execution_venue_comparison.md"),
            },
            "execution_diagnostics_summary": {
                "execution_diagnostics_report_path": (
                    "data/reports/execution_venue_diagnostics.md"
                ),
            },
            "execution_gap_history_summary": {
                "execution_gap_history_report_path": ("data/reports/execution_gap_history.md"),
            },
            "execution_state_comparison_summary": {
                "execution_state_comparison_report_path": (
                    "data/reports/execution_state_comparison_history.md"
                ),
            },
            "execution_snapshot_drift_summary": {
                "execution_snapshot_drift_report_path": (
                    "data/reports/execution_snapshot_drift_history.md"
                ),
            },
            "execution_drift_overview_summary": {
                "report_path": "data/reports/execution_drift_overview.md",
            },
        },
    ) == {
        "paper_vs_backtest_comparison_report": ("data/reports/paper_vs_backtest_comparison.md"),
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "execution_snapshot_report": "data/reports/execution_snapshot.md",
        "execution_venue_comparison_report": ("data/reports/execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": ("data/reports/execution_venue_diagnostics.md"),
        "execution_gap_history_report": "data/reports/execution_gap_history.md",
        "execution_state_comparison_report": ("data/reports/execution_state_comparison_history.md"),
        "execution_snapshot_drift_report": ("data/reports/execution_snapshot_drift_history.md"),
        "execution_drift_overview_report": "data/reports/execution_drift_overview.md",
    }
