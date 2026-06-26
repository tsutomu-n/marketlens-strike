from pathlib import Path

from sis.reports.evidence_navigation import quick_navigation, related_reports, reports_dir


def test_reports_dir_uses_data_reports_child() -> None:
    assert reports_dir(Path("data")) == Path("data/reports")


def test_quick_navigation_uses_default_phase_gate_path_and_filters_live_evidence() -> None:
    navigation = quick_navigation(
        Path("data"),
        phase_gate_summary={},
        readiness_summary={"live_evidence_report_path": 123},
    )

    assert navigation == {
        "go_no_go_report": "data/research/go_no_go_report.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
    }


def test_quick_navigation_prefers_summary_report_paths() -> None:
    navigation = quick_navigation(
        Path("data"),
        phase_gate_summary={"phase_gate_review_report_path": "custom/phase_gate.md"},
        readiness_summary={"live_evidence_report_path": "docs/live_evidence.md"},
    )

    assert navigation["phase_gate_review_report"] == "custom/phase_gate.md"
    assert navigation["live_evidence_report"] == "docs/live_evidence.md"


def test_related_reports_includes_execution_report_paths_in_expected_order() -> None:
    reports = related_reports(
        Path("data"),
        phase_gate_summary={"phase_gate_review_report_path": "custom/phase_gate.md"},
        readiness_summary={"live_evidence_report_path": "docs/live_evidence.md"},
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
        "operations_dashboard_report",
        "ops_review_report",
        "current_state_index_report",
        "readiness_snapshot_report",
        "paper_operations_runbook_report",
        "paper_vs_backtest_comparison_report",
        "remediation_scoreboard_report",
        "live_evidence_report",
        "execution_snapshot_report",
        "execution_venue_comparison_report",
        "execution_venue_diagnostics_report",
        "execution_gap_history_report",
        "execution_state_comparison_report",
        "execution_snapshot_drift_report",
        "execution_drift_overview_report",
    ]
    assert reports["phase_gate_review_report"] == "custom/phase_gate.md"
    assert reports["live_evidence_report"] == "docs/live_evidence.md"
    assert reports["execution_snapshot_report"] == "data/reports/execution_snapshot.md"
    assert reports["execution_drift_overview_report"] == "data/reports/execution_drift_overview.md"
