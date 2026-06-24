from __future__ import annotations

from pathlib import Path

from sis.reports.current_state_index_navigation import (
    live_evidence_report_path,
    quick_navigation,
    related_reports,
    remediation_fields_from_sources,
    report_path_for_summary,
)


def test_remediation_fields_from_sources_later_sources_override_earlier() -> None:
    operations_dashboard = {
        "timeline_latest_remediation_planner_status": "operations-dashboard",
        "timeline_latest_remediation_session_status": "operations-dashboard-session",
    }
    operations_bundle = {
        "timeline_latest_remediation_planner_status": "operations-bundle",
    }
    audit_dashboard = {
        "timeline_latest_remediation_planner_status": "audit-dashboard",
    }
    audit_bundle = {
        "timeline_latest_remediation_planner_status": "audit-bundle",
        "unrelated": "ignored",
    }

    assert remediation_fields_from_sources(
        operations_dashboard,
        operations_bundle,
        audit_dashboard,
        audit_bundle,
    ) == {
        "timeline_latest_remediation_planner_status": "audit-bundle",
        "timeline_latest_remediation_session_status": "operations-dashboard-session",
    }


def test_report_path_for_summary_uses_reports_sibling_for_ops_summary() -> None:
    assert report_path_for_summary(Path("data/ops/current_state_index.json"), "audit.md") == (
        "data/reports/audit.md"
    )


def test_report_path_for_summary_uses_summary_parent_for_non_ops_path() -> None:
    assert report_path_for_summary(Path("tmp/current_state_index.json"), "audit.md") == (
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


def test_quick_navigation_filters_to_primary_current_state_reports() -> None:
    restart_pointers = {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "remediation_scoreboard_report": "",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
    }

    assert quick_navigation(restart_pointers, "data/reports/phase_gate_review.md") == {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }


def test_related_reports_includes_ordered_current_state_restart_reports() -> None:
    restart_pointers = {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": "data/reports/remediation_session_checkpoint.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_report": "data/reports/remediation_command_results.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }

    assert related_reports(restart_pointers, "data/reports/phase_gate_review.md") == {
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_session_checkpoint_report": "data/reports/remediation_session_checkpoint.md",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_report": "data/reports/remediation_command_results.md",
        "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run-1.md",
    }
