from pathlib import Path

from sis.reports.remediation_execution_plan_navigation import (
    quick_navigation,
    related_reports,
)


def test_quick_navigation_omits_missing_output_path() -> None:
    assert quick_navigation(None) == {}


def test_quick_navigation_uses_execution_plan_report_siblings() -> None:
    out_path = Path("data/reports/remediation_execution_plan.md")

    assert quick_navigation(out_path) == {
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
    }


def test_related_reports_omits_missing_output_path() -> None:
    assert related_reports(None) == {}


def test_related_reports_uses_expected_report_siblings() -> None:
    out_path = Path("data/reports/remediation_execution_plan.md")

    assert related_reports(out_path) == {
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_session_checkpoint_report": ("data/reports/remediation_session_checkpoint.md"),
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_report": ("data/reports/remediation_command_results.md"),
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
    }
