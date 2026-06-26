from pathlib import Path

from sis.reports.go_no_go_markdown_navigation import (
    quick_navigation,
    related_reports,
    reports_dir,
)


def test_reports_dir_uses_research_sibling_reports_dir(tmp_path: Path) -> None:
    out_path = tmp_path / "data/research/go_no_go_report.md"

    assert reports_dir(out_path) == tmp_path / "data/reports"


def test_quick_navigation_uses_expected_report_order(tmp_path: Path) -> None:
    out_path = tmp_path / "data/research/go_no_go_report.md"

    navigation = quick_navigation(
        out_path,
        phase_gate_summary={"phase_gate_review_report_path": "data/reports/phase_gate_review.md"},
        readiness_summary={"readiness_next_phase_candidate": "Stay Phase 1"},
    )

    assert navigation == {
        "go_no_go_report": str(out_path),
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "current_state_index_report": str(tmp_path / "data/reports/current_state_index.md"),
        "readiness_snapshot_report": str(tmp_path / "data/reports/readiness_snapshot.md"),
        "paper_operations_runbook_report": str(
            tmp_path / "data/reports/paper_operations_runbook.md"
        ),
    }


def test_related_reports_include_execution_report_paths(tmp_path: Path) -> None:
    out_path = tmp_path / "data/research/go_no_go_report.md"

    reports = related_reports(
        out_path,
        phase_gate_summary={"phase_gate_review_report_path": "data/reports/phase_gate_review.md"},
        readiness_summary={"readiness_next_phase_candidate": "Stay Phase 1"},
        execution_summary={"report_path": "data/reports/execution_snapshot.md"},
        execution_comparison_summary={"report_path": "data/reports/execution_venue_comparison.md"},
        execution_diagnostics_summary={
            "report_path": "data/reports/execution_venue_diagnostics.md"
        },
        execution_gap_history_summary={"report_path": "data/reports/execution_gap_history.md"},
        execution_state_comparison_summary={
            "report_path": "data/reports/execution_state_comparison_history.md"
        },
        execution_snapshot_drift_summary={
            "report_path": "data/reports/execution_snapshot_drift_history.md"
        },
        execution_drift_overview_summary={
            "report_path": "data/reports/execution_drift_overview.md"
        },
    )

    assert list(reports) == [
        "go_no_go_report",
        "phase_gate_review_report",
        "current_state_index_report",
        "readiness_snapshot_report",
        "operations_dashboard_report",
        "paper_operations_runbook_report",
        "execution_snapshot_report",
        "execution_venue_comparison_report",
        "execution_venue_diagnostics_report",
        "execution_gap_history_report",
        "execution_state_comparison_report",
        "execution_snapshot_drift_report",
        "execution_drift_overview_report",
    ]
    assert reports["execution_snapshot_report"] == "data/reports/execution_snapshot.md"
    assert (
        reports["execution_venue_comparison_report"] == "data/reports/execution_venue_comparison.md"
    )
    assert reports["execution_drift_overview_report"] == "data/reports/execution_drift_overview.md"
