from __future__ import annotations

from sis.reports.live_evidence_sections import (
    quick_navigation_html_metrics,
    quick_navigation_lines,
    remediation_html_metrics,
    remediation_markdown_lines,
    restart_pointer_lines,
)


def test_live_evidence_section_helpers_render_markdown_lines() -> None:
    readiness_summary = {
        "timeline_latest_remediation_planner_status": "stalled",
        "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts",
        "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run123.md",
    }
    phase_gate_summary = {
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
    }

    remediation_lines = remediation_markdown_lines(readiness_summary)
    restart_lines = restart_pointer_lines(readiness_summary)
    navigation_lines = quick_navigation_lines(readiness_summary, phase_gate_summary)

    assert "- planner_status: `stalled`" in remediation_lines
    assert "- planner_next_best_command: `uv run sis validate-artifacts`" in remediation_lines
    assert (
        "- live_evidence_report: `docs/live_evidence_reports/live_evidence_report_run123.md`"
        in restart_lines
    )
    assert "- phase_gate_review_report: `data/reports/phase_gate_review.md`" in navigation_lines


def test_live_evidence_section_helpers_escape_html_values() -> None:
    readiness_summary = {
        "timeline_latest_remediation_planner_status": "<stalled>",
        "timeline_latest_remediation_planner_next_best_command": "uv run sis <validate>",
        "current_state_index_report": "data/reports/current_state_index.md",
    }
    phase_gate_summary = {
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
    }

    remediation_html = remediation_html_metrics(readiness_summary)
    navigation_html = quick_navigation_html_metrics(readiness_summary, phase_gate_summary)

    assert "&lt;stalled&gt;" in remediation_html
    assert "uv run sis &lt;validate&gt;" in remediation_html
    assert "Current State Index Report" in navigation_html
    assert "data/reports/current_state_index.md" in navigation_html
