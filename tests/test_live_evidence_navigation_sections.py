from __future__ import annotations

from sis.reports.live_evidence_navigation_sections import (
    quick_navigation_html_metrics,
    quick_navigation_lines,
    related_report_html_metrics,
    related_report_lines,
    restart_pointer_html_metrics,
    restart_pointer_lines,
)


def _readiness_summary() -> dict[str, object]:
    return {
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": None,
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_<run>.md",
    }


def _phase_gate_summary() -> dict[str, object]:
    return {
        "phase_gate_review_report_path": "data/reports/phase_gate_review_<x>.md",
    }


def test_restart_pointer_lines_preserve_order_and_skip_none() -> None:
    assert restart_pointer_lines(_readiness_summary()) == [
        "- readiness_snapshot_report: `data/reports/readiness_snapshot.md`",
        "- current_state_index_report: `data/reports/current_state_index.md`",
        "- remediation_scoreboard_report: `data/reports/remediation_scoreboard.md`",
        "- remediation_session_report: `data/reports/remediation_session.md`",
        ("- remediation_execution_plan_report: `data/reports/remediation_execution_plan.md`"),
        "- remediation_planner_report: `data/reports/remediation_planner.md`",
        ("- live_evidence_report: `docs/live_evidence_reports/live_evidence_report_<run>.md`"),
    ]


def test_navigation_lines_preserve_order_and_skip_none() -> None:
    assert quick_navigation_lines(_readiness_summary(), _phase_gate_summary()) == [
        "- current_state_index_report: `data/reports/current_state_index.md`",
        "- readiness_snapshot_report: `data/reports/readiness_snapshot.md`",
        "- phase_gate_review_report: `data/reports/phase_gate_review_<x>.md`",
        "- remediation_scoreboard_report: `data/reports/remediation_scoreboard.md`",
        ("- live_evidence_report: `docs/live_evidence_reports/live_evidence_report_<run>.md`"),
    ]

    assert related_report_lines(_readiness_summary(), _phase_gate_summary()) == [
        "- phase_gate_review_report: `data/reports/phase_gate_review_<x>.md`",
        "- readiness_snapshot_report: `data/reports/readiness_snapshot.md`",
        "- current_state_index_report: `data/reports/current_state_index.md`",
        "- remediation_scoreboard_report: `data/reports/remediation_scoreboard.md`",
        "- remediation_session_report: `data/reports/remediation_session.md`",
        ("- remediation_execution_plan_report: `data/reports/remediation_execution_plan.md`"),
        "- remediation_planner_report: `data/reports/remediation_planner.md`",
        ("- live_evidence_report: `docs/live_evidence_reports/live_evidence_report_<run>.md`"),
    ]


def test_navigation_html_metrics_escape_values_and_preserve_labels() -> None:
    restart_html = restart_pointer_html_metrics(_readiness_summary())
    quick_html = quick_navigation_html_metrics(_readiness_summary(), _phase_gate_summary())
    related_html = related_report_html_metrics(_readiness_summary(), _phase_gate_summary())

    assert "Readiness Snapshot Report" in restart_html
    assert "Remediation Session Checkpoint Report" not in restart_html
    assert "live_evidence_report_&lt;run&gt;.md" in restart_html
    assert "Phase Gate Review Report" in quick_html
    assert "phase_gate_review_&lt;x&gt;.md" in quick_html
    assert related_html.index("Phase Gate Review Report") < related_html.index(
        "Readiness Snapshot Report"
    )
