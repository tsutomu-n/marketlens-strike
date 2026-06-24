from __future__ import annotations

from pathlib import Path

from sis.reports.readiness_snapshot_navigation import (
    live_evidence_report_path,
    quick_navigation,
    related_reports,
    remediation_fields_from_sources,
    report_path_for_summary,
)


def test_remediation_fields_prefer_current_state_then_operations() -> None:
    current_state = {
        "timeline_latest_remediation_planner_status": "current-ready",
        "timeline_latest_remediation_execution_plan_status": None,
    }
    operations = {
        "timeline_latest_remediation_planner_status": "operations-stale",
        "timeline_latest_remediation_execution_plan_status": "operations-ready",
        "unrelated": "ignored",
    }

    assert remediation_fields_from_sources(current_state, operations) == {
        "timeline_latest_remediation_planner_status": "current-ready",
        "timeline_latest_remediation_execution_plan_status": "operations-ready",
    }


def test_report_path_for_summary_uses_reports_sibling_for_ops_summary() -> None:
    assert report_path_for_summary(Path("data/ops/readiness_snapshot.json"), "audit.md") == (
        "data/reports/audit.md"
    )


def test_report_path_for_summary_uses_summary_parent_for_non_ops_path() -> None:
    assert report_path_for_summary(Path("tmp/readiness_snapshot.json"), "audit.md") == (
        "tmp/reports/audit.md"
    )


def test_report_path_for_summary_omits_missing_path() -> None:
    assert report_path_for_summary(None, "audit.md") is None


def test_live_evidence_report_path_prefers_summary_run_id() -> None:
    assert (
        live_evidence_report_path(
            Path("data/ops/live_evidence_summary_from-path.json"),
            {"run_id": "from-summary"},
        )
        == "docs/live_evidence_reports/live_evidence_report_from-summary.md"
    )


def test_live_evidence_report_path_falls_back_to_summary_filename() -> None:
    assert (
        live_evidence_report_path(
            Path("data/ops/live_evidence_summary_from-path.json"),
            {},
        )
        == "docs/live_evidence_reports/live_evidence_report_from-path.md"
    )


def test_live_evidence_report_path_omits_unrecognized_filename() -> None:
    assert live_evidence_report_path(Path("data/ops/latest_live_evidence.json"), {}) is None


def test_quick_navigation_filters_to_primary_restart_reports() -> None:
    restart_pointers = {
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "remediation_scoreboard_report": "",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
        "remediation_session_report": "data/reports/remediation_session.md",
    }

    assert quick_navigation(restart_pointers, "data/reports/phase_gate_review.md") == {
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }


def test_related_reports_includes_ordered_remediation_restart_reports() -> None:
    restart_pointers = {
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": "data/reports/remediation_session_checkpoint.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }

    assert related_reports(restart_pointers, "data/reports/phase_gate_review.md") == {
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": "data/reports/remediation_session_checkpoint.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }
