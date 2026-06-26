from pathlib import Path

from sis.reports.lifecycle_navigation import (
    nested_report_path,
    quick_navigation,
    related_reports,
)


def test_quick_navigation_omits_missing_output_path() -> None:
    assert quick_navigation(None, {}) == {}


def test_quick_navigation_filters_live_evidence_and_preserves_order() -> None:
    out_path = Path("data/reports/strategy_lifecycle_report.md")

    navigation = quick_navigation(
        out_path,
        {"live_evidence_report_path": 123},
    )

    assert navigation == {
        "strategy_lifecycle_report": "data/reports/strategy_lifecycle_report.md",
        "weekly_review_report": "data/reports/weekly_strategy_review.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
    }


def test_quick_navigation_includes_live_evidence_path_when_present() -> None:
    navigation = quick_navigation(
        Path("data/reports/strategy_lifecycle_report.md"),
        {"live_evidence_report_path": "docs/live_evidence_reports/latest.md"},
    )

    assert navigation["live_evidence_report"] == "docs/live_evidence_reports/latest.md"


def test_nested_report_path_prefers_flat_key_before_nested_report_path() -> None:
    payload = {
        "execution_drift_overview_report_path": "data/reports/flat.md",
        "execution_drift_overview_summary": {"report_path": "data/reports/nested.md"},
    }

    assert (
        nested_report_path(
            payload,
            "execution_drift_overview_summary",
            "execution_drift_overview_report_path",
        )
        == "data/reports/flat.md"
    )


def test_nested_report_path_falls_back_to_nested_report_path() -> None:
    payload = {
        "execution_drift_overview_summary": {"report_path": "data/reports/nested.md"},
    }

    assert (
        nested_report_path(
            payload,
            "execution_drift_overview_summary",
            "execution_drift_overview_report_path",
        )
        == "data/reports/nested.md"
    )


def test_related_reports_uses_expected_report_order_and_nested_path() -> None:
    out_path = Path("data/reports/strategy_lifecycle_report.md")

    reports = related_reports(
        out_path,
        {
            "execution_drift_overview_summary": {
                "report_path": "data/reports/execution_drift_overview.md",
            },
            "live_evidence_report_path": "docs/live_evidence_reports/latest.md",
        },
    )

    assert reports == {
        "strategy_lifecycle_report": "data/reports/strategy_lifecycle_report.md",
        "weekly_review_report": "data/reports/weekly_strategy_review.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "ops_review_report": "data/reports/ops_review.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "go_no_go_report": "data/research/go_no_go_report.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "paper_vs_backtest_comparison_report": ("data/reports/paper_vs_backtest_comparison.md"),
        "execution_drift_overview_report": "data/reports/execution_drift_overview.md",
        "live_evidence_report": "docs/live_evidence_reports/latest.md",
    }
