from __future__ import annotations

from pathlib import Path

from sis.reports.audit_bundle_history_helpers import note_value
from sis.reports.audit_bundle_history_helpers import note_values
from sis.reports.audit_bundle_history_helpers import quick_navigation
from sis.reports.audit_bundle_history_helpers import related_reports
from sis.reports.audit_bundle_history_helpers import report_path_fields
from sis.reports.audit_bundle_history_helpers import reports_dir
from sis.reports.audit_bundle_history_helpers import summary_section_lines
from sis.reports.audit_bundle_history_helpers import latest_note_summary_fields


def test_note_helpers_match_prefix_and_coerce_values() -> None:
    notes: list[object] = [
        "status=ok",
        123,
        "status=degraded",
        "other=value",
    ]

    assert note_value(notes, "status=") == "ok"
    assert note_value(notes, "missing=") is None
    assert note_values(notes, "status=") == ["ok", "degraded"]
    assert note_values(notes, "123") == [""]


def test_reports_dir_uses_ops_parent_when_operation_chain_is_under_ops() -> None:
    assert reports_dir(Path("data/ops/operation_manifests.jsonl")) == Path("data/reports")
    assert reports_dir(Path("data/custom/operation_manifests.jsonl")) == Path("data/custom/reports")
    assert reports_dir(None) is None


def test_quick_navigation_filters_missing_values_in_expected_order() -> None:
    summary = {
        "audit_bundle_history_report_path": "reports/history.md",
        "audit_dashboard_report_path": "",
        "current_state_index_report_path": "reports/current.md",
        "readiness_snapshot_report_path": "reports/readiness.md",
        "latest_phase_gate_review_report_path": 123,
        "remediation_scoreboard_report_path": "reports/scoreboard.md",
    }

    assert quick_navigation(summary) == {
        "audit_bundle_history_report": "reports/history.md",
        "current_state_index_report": "reports/current.md",
        "readiness_snapshot_report": "reports/readiness.md",
        "remediation_scoreboard_report": "reports/scoreboard.md",
    }


def test_related_reports_preserves_expected_order_and_filters_missing_values() -> None:
    summary = {
        "audit_bundle_history_report_path": "reports/history.md",
        "audit_timeline_report_path": "reports/timeline.md",
        "audit_dashboard_report_path": None,
        "audit_bundle_report_path": "reports/bundle.md",
        "operations_audit_pack_report_path": "reports/pack.md",
        "current_state_index_report_path": "",
        "readiness_snapshot_report_path": "reports/readiness.md",
        "latest_phase_gate_review_report_path": "reports/phase.md",
        "remediation_scoreboard_report_path": "reports/scoreboard.md",
    }

    assert related_reports(summary) == {
        "audit_bundle_history_report": "reports/history.md",
        "audit_timeline_report": "reports/timeline.md",
        "audit_bundle_report": "reports/bundle.md",
        "operations_audit_pack_report": "reports/pack.md",
        "readiness_snapshot_report": "reports/readiness.md",
        "phase_gate_review_report": "reports/phase.md",
        "remediation_scoreboard_report": "reports/scoreboard.md",
    }


def test_report_path_fields_build_expected_history_related_paths() -> None:
    fields = report_path_fields(
        out_path=Path("data/reports/audit_bundle_history.md"),
        reports_dir=Path("data/reports"),
    )

    assert fields == {
        "audit_bundle_history_report_path": "data/reports/audit_bundle_history.md",
        "audit_timeline_report_path": "data/reports/audit_timeline.md",
        "audit_dashboard_report_path": "data/reports/audit_dashboard.md",
        "audit_bundle_report_path": "data/reports/audit_bundle_manifest.md",
        "operations_audit_pack_report_path": "data/reports/operations_audit_pack.md",
        "current_state_index_report_path": "data/reports/current_state_index.md",
        "readiness_snapshot_report_path": "data/reports/readiness_snapshot.md",
        "remediation_scoreboard_report_path": "data/reports/remediation_scoreboard.md",
    }


def test_report_path_fields_preserve_none_without_report_directory() -> None:
    assert report_path_fields(out_path=None, reports_dir=None) == {
        "audit_bundle_history_report_path": None,
        "audit_timeline_report_path": None,
        "audit_dashboard_report_path": None,
        "audit_bundle_report_path": None,
        "operations_audit_pack_report_path": None,
        "current_state_index_report_path": None,
        "readiness_snapshot_report_path": None,
        "remediation_scoreboard_report_path": None,
    }


def test_summary_section_lines_preserve_exact_field_order_and_format() -> None:
    expected_keys = (
        "snapshot_count",
        "ok_count",
        "latest_status",
        "latest_run_id",
        "latest_created_at",
        "latest_execution_overall_status",
        "latest_execution_venue_count",
        "latest_execution_comparison_all_registries_present",
        "latest_execution_gap_history_status",
        "latest_execution_drift_overview_status",
        "latest_execution_drift_overview_diagnostics_alignment_match",
        "latest_execution_drift_overview_state_comparison_mismatching_count",
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count",
        "latest_execution_gap_history_diagnostics_status",
        "latest_execution_state_comparison_status_match",
        "latest_execution_state_comparison_mismatching_count",
        "latest_remediation_planner_status",
        "latest_remediation_planner_next_best_command",
        "latest_remediation_planner_feedback_priority_reason",
        "latest_remediation_execution_plan_status",
        "latest_remediation_execution_plan_next_action_command",
        "latest_remediation_execution_plan_feedback_priority_reason",
        "latest_remediation_session_status",
        "latest_remediation_session_next_pending_command",
        "latest_remediation_session_feedback_priority_reason",
        "latest_remediation_checkpoint_status",
        "latest_remediation_checkpoint_next_action_command",
        "latest_remediation_checkpoint_feedback_priority_reason",
        "latest_remediation_scoreboard_status",
        "latest_remediation_scoreboard_next_action_command",
        "latest_remediation_scoreboard_feedback_priority_reason",
        "latest_readiness_next_phase",
        "latest_readiness_execution_ready",
        "latest_phase_gate_decision",
        "latest_phase2_entry_allowed",
        "latest_phase_gate_reason",
        "latest_phase_gate_strict_validation_passed",
        "latest_phase_gate_strict_validation_issue_count",
        "latest_phase_gate_checked_files",
        "latest_phase_gate_review_report_path",
        "execution_overall_status",
        "execution_venue_count",
    )
    summary = {key: f"value-{index}" for index, key in enumerate(expected_keys)}

    assert summary_section_lines(summary) == [
        "## Summary",
        "",
        *[f"- {key}: value-{index}" for index, key in enumerate(expected_keys)],
        "",
    ]


def test_latest_note_summary_fields_preserve_nested_and_flat_note_outputs() -> None:
    fields = latest_note_summary_fields(
        [
            "execution_drift_overview_status=degraded",
            "execution_drift_overview_diagnostics_alignment_match=False",
            "execution_drift_overview_state_comparison_mismatching_count=1",
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=2",
            "execution_gap_history_latest_status=ok",
            "execution_gap_history_latest_diagnostics_status=degraded",
            "execution_state_comparison_latest_status_match=False",
            "execution_state_comparison_mismatching_count=3",
            "readiness_next_phase=Phase 1",
            "readiness_execution_ready=False",
            "phase_gate_decision=CONDITIONAL_GO",
            "phase2_entry_allowed=False",
            "phase_gate_reason=needs_more_evidence",
            "phase_gate_strict_validation_passed=False",
            "phase_gate_strict_validation_issue_count=2",
            "phase_gate_checked_files=7",
            "phase_gate_review_report_path=data/reports/phase_gate_review.md",
            "phase_gate_issue_1=data/a.json: missing",
            "planner_status=stalled",
            "next_best_command=uv run sis validate-artifacts --strict",
            "next_feedback_priority_reason=evaluation_failed",
            "execution_plan_status=ready",
            "next_action_command=uv run sis phase-gate-review",
            "next_action_feedback_priority_reason=needs_review",
            "session_status=ready_for_dry_run",
            "next_pending_command=uv run sis monitoring-status",
            "next_pending_feedback_priority_reason=waiting",
            "checkpoint_status=retry_pending",
            "scoreboard_status=retrying",
        ]
    )

    assert fields["latest_execution_drift_overview_summary"] == {
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_diagnostics_alignment_match": "False",
        "execution_drift_overview_state_comparison_mismatching_count": "1",
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": "2",
    }
    assert fields["latest_execution_gap_history_summary"] == {
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "degraded",
    }
    assert fields["latest_execution_state_comparison_summary"] == {
        "execution_state_comparison_latest_status_match": "False",
        "execution_state_comparison_mismatching_count": "3",
    }
    assert fields["latest_readiness_summary"] == {
        "readiness_next_phase_candidate": "Phase 1",
        "readiness_execution_ready": "False",
    }
    assert fields["latest_phase_gate_summary"]["phase_gate_decision"] == "CONDITIONAL_GO"
    assert fields["latest_phase_gate_summary"]["phase_gate_strict_validation_issues"] == [
        "data/a.json: missing"
    ]
    assert fields["latest_execution_drift_overview_status"] == "degraded"
    assert fields["latest_execution_gap_history_diagnostics_status"] == "degraded"
    assert fields["latest_readiness_next_phase"] == "Phase 1"
    assert fields["latest_phase_gate_issue_previews"] == ["data/a.json: missing"]
    assert fields["latest_remediation_planner_status"] == "stalled"
    assert fields["latest_remediation_planner_next_best_command"] == (
        "uv run sis validate-artifacts --strict"
    )
    assert fields["latest_remediation_execution_plan_next_action_command"] == (
        "uv run sis phase-gate-review"
    )
    assert fields["latest_remediation_checkpoint_next_action_command"] == (
        "uv run sis phase-gate-review"
    )
    assert fields["latest_remediation_scoreboard_next_action_command"] == (
        "uv run sis phase-gate-review"
    )
