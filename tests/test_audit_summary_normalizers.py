from __future__ import annotations

from sis.reports import summary_normalizers
from sis.reports.audit_summary_normalizers import (
    audit_bundle_flat_fields,
    audit_bundle_history_flat_fields,
    audit_dashboard_flat_fields,
    audit_summary_fields,
    audit_timeline_flat_fields,
    ops_review_flat_fields,
)


def test_audit_dashboard_flat_fields_accept_prefixed_and_unprefixed_values() -> None:
    assert audit_dashboard_flat_fields(
        {
            "audit_overall_status": "prefixed",
            "overall_status": "unprefixed",
            "latest_operation": "timeline",
            "audit_latest_operation": "audit-latest",
            "entry_count": 3,
            "bundle_snapshot_count": 5,
        }
    ) == {
        "audit_overall_status": "unprefixed",
        "audit_latest_operation": "timeline",
        "audit_entry_count": 3,
        "audit_bundle_snapshot_count": 5,
    }


def test_audit_bundle_flat_fields_prefers_unprefixed_counts() -> None:
    assert audit_bundle_flat_fields(
        {
            "bundle_history_snapshot_count": 8,
            "audit_bundle_history_snapshot_count": 7,
            "bundle_history_ok_count": 6,
            "audit_bundle_history_ok_count": 5,
        }
    ) == {
        "audit_bundle_history_snapshot_count": 8,
        "audit_bundle_history_ok_count": 6,
    }


def test_audit_summary_fields_combines_dashboard_and_bundle_fields() -> None:
    assert audit_summary_fields(
        {
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "entry_count": 4,
        },
        {
            "bundle_history_snapshot_count": 9,
            "bundle_history_ok_count": 8,
        },
    ) == {
        "overall_status": "ok",
        "latest_operation": "audit_bundle_snapshot",
        "bundle_history_snapshot_count": 9,
        "audit_overall_status": "ok",
        "audit_latest_operation": "audit_bundle_snapshot",
        "audit_bundle_history_snapshot_count": 9,
    }


def test_audit_timeline_flat_fields_preserves_prefixed_fallbacks() -> None:
    assert audit_timeline_flat_fields(
        {
            "latest_operation": "ops_snapshot",
            "latest_status": "ok",
            "audit_entry_count": 4,
            "timeline_latest_execution_overall_status": "degraded",
            "latest_execution_venue_count": 2,
            "latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_scoreboard_next_action_command": (
                "uv run sis remediation-scoreboard"
            ),
        }
    ) == {
        "timeline_latest_operation": "ops_snapshot",
        "timeline_latest_status": "ok",
        "audit_entry_count": 4,
        "timeline_latest_execution_overall_status": "degraded",
        "timeline_latest_execution_venue_count": 2,
        "timeline_latest_execution_comparison_all_registries_present": None,
        "timeline_latest_execution_gap_history_status": None,
        "timeline_latest_execution_gap_history_diagnostics_status": None,
        "timeline_latest_readiness_execution_ready": None,
        "timeline_latest_remediation_planner_status": "stalled",
        "timeline_latest_remediation_planner_next_best_command": None,
        "timeline_latest_remediation_planner_feedback_priority_reason": None,
        "timeline_latest_remediation_execution_plan_status": None,
        "timeline_latest_remediation_execution_plan_next_action_command": None,
        "timeline_latest_remediation_execution_plan_feedback_priority_reason": None,
        "timeline_latest_remediation_session_status": None,
        "timeline_latest_remediation_session_next_pending_command": None,
        "timeline_latest_remediation_session_feedback_priority_reason": None,
        "timeline_latest_remediation_checkpoint_status": None,
        "timeline_latest_remediation_checkpoint_next_action_command": None,
        "timeline_latest_remediation_checkpoint_feedback_priority_reason": None,
        "timeline_latest_remediation_scoreboard_status": None,
        "timeline_latest_remediation_scoreboard_next_action_command": (
            "uv run sis remediation-scoreboard"
        ),
        "timeline_latest_remediation_scoreboard_feedback_priority_reason": None,
    }


def test_audit_bundle_history_flat_fields_preserves_execution_fallbacks() -> None:
    assert audit_bundle_history_flat_fields(
        {
            "snapshot_count": 4,
            "ok_count": 3,
            "bundle_history_latest_execution_overall_status": "degraded",
            "latest_execution_venue_count": 2,
            "latest_readiness_execution_ready": False,
        }
    ) == {
        "bundle_history_snapshot_count": 4,
        "bundle_history_ok_count": 3,
        "bundle_history_latest_execution_overall_status": "degraded",
        "bundle_history_latest_execution_venue_count": 2,
        "bundle_history_latest_execution_comparison_all_registries_present": None,
        "bundle_history_latest_execution_gap_history_status": None,
        "bundle_history_latest_execution_gap_history_diagnostics_status": None,
        "bundle_history_latest_readiness_execution_ready": False,
    }


def test_ops_review_flat_fields_uses_ops_prefixed_keys() -> None:
    assert ops_review_flat_fields(
        {
            "operations_count": 12,
            "latest_operation": "paper_operations_cycle",
            "latest_status": "ok",
            "latest_scheduled_for": "2026-05-25T00:00:00Z",
            "monitoring_status": "ok",
            "daemon_dry_run_status": "pass",
        }
    ) == {
        "ops_operations_count": 12,
        "ops_latest_operation": "paper_operations_cycle",
        "ops_latest_status": "ok",
        "ops_latest_scheduled_for": "2026-05-25T00:00:00Z",
        "ops_monitoring_status": "ok",
        "ops_daemon_dry_run_status": "pass",
    }


def test_summary_normalizers_keeps_audit_compatibility_aliases() -> None:
    assert summary_normalizers.audit_dashboard_flat_fields is audit_dashboard_flat_fields
    assert summary_normalizers.audit_bundle_flat_fields is audit_bundle_flat_fields
    assert summary_normalizers.audit_summary_fields is audit_summary_fields
    assert summary_normalizers.audit_timeline_flat_fields is audit_timeline_flat_fields
    assert summary_normalizers.audit_bundle_history_flat_fields is audit_bundle_history_flat_fields
    assert summary_normalizers.ops_review_flat_fields is ops_review_flat_fields
