from __future__ import annotations

from typing import Any, Mapping


def audit_dashboard_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    overall_status = payload.get("overall_status") or payload.get("audit_overall_status")
    latest_operation = (
        payload.get("timeline_latest_operation")
        or payload.get("latest_operation")
        or payload.get("audit_latest_operation")
    )
    audit_entry_count = (
        payload.get("audit_entry_count")
        if payload.get("audit_entry_count") is not None
        else payload.get("entry_count")
    )
    audit_bundle_snapshot_count = (
        payload.get("audit_bundle_snapshot_count")
        if payload.get("audit_bundle_snapshot_count") is not None
        else payload.get("bundle_snapshot_count")
    )
    return {
        "audit_overall_status": overall_status,
        "audit_latest_operation": latest_operation,
        "audit_entry_count": audit_entry_count,
        "audit_bundle_snapshot_count": audit_bundle_snapshot_count,
    }


def audit_bundle_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return {
        "audit_bundle_history_snapshot_count": (
            payload.get("bundle_history_snapshot_count")
            if payload.get("bundle_history_snapshot_count") is not None
            else payload.get("audit_bundle_history_snapshot_count")
        ),
        "audit_bundle_history_ok_count": (
            payload.get("bundle_history_ok_count")
            if payload.get("bundle_history_ok_count") is not None
            else payload.get("audit_bundle_history_ok_count")
        ),
    }


def audit_summary_fields(
    audit_dashboard_summary: Mapping[str, Any] | None,
    audit_bundle_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard_summary)
    audit_bundle_fields = audit_bundle_flat_fields(audit_bundle_summary)
    overall_status = audit_dashboard_fields.get("audit_overall_status")
    latest_operation = audit_dashboard_fields.get("audit_latest_operation")
    bundle_history_snapshot_count = audit_bundle_fields.get("audit_bundle_history_snapshot_count")
    return {
        "overall_status": overall_status,
        "latest_operation": latest_operation,
        "bundle_history_snapshot_count": bundle_history_snapshot_count,
        "audit_overall_status": overall_status,
        "audit_latest_operation": latest_operation,
        "audit_bundle_history_snapshot_count": bundle_history_snapshot_count,
    }


def audit_timeline_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return {
        "timeline_latest_operation": payload.get("latest_operation"),
        "timeline_latest_status": payload.get("latest_status"),
        "audit_entry_count": payload.get("audit_entry_count"),
        "timeline_latest_execution_overall_status": payload.get(
            "latest_execution_overall_status",
            payload.get("timeline_latest_execution_overall_status"),
        ),
        "timeline_latest_execution_venue_count": payload.get(
            "latest_execution_venue_count",
            payload.get("timeline_latest_execution_venue_count"),
        ),
        "timeline_latest_execution_comparison_all_registries_present": payload.get(
            "latest_execution_comparison_all_registries_present",
            payload.get("timeline_latest_execution_comparison_all_registries_present"),
        ),
        "timeline_latest_execution_gap_history_status": payload.get(
            "latest_execution_gap_history_status",
            payload.get("timeline_latest_execution_gap_history_status"),
        ),
        "timeline_latest_execution_gap_history_diagnostics_status": payload.get(
            "latest_execution_gap_history_diagnostics_status",
            payload.get("timeline_latest_execution_gap_history_diagnostics_status"),
        ),
        "timeline_latest_readiness_execution_ready": payload.get(
            "latest_readiness_execution_ready",
            payload.get("timeline_latest_readiness_execution_ready"),
        ),
        "timeline_latest_remediation_planner_status": payload.get(
            "latest_remediation_planner_status",
            payload.get("timeline_latest_remediation_planner_status"),
        ),
        "timeline_latest_remediation_planner_next_best_command": payload.get(
            "latest_remediation_planner_next_best_command",
            payload.get("timeline_latest_remediation_planner_next_best_command"),
        ),
        "timeline_latest_remediation_planner_feedback_priority_reason": payload.get(
            "latest_remediation_planner_feedback_priority_reason",
            payload.get("timeline_latest_remediation_planner_feedback_priority_reason"),
        ),
        "timeline_latest_remediation_execution_plan_status": payload.get(
            "latest_remediation_execution_plan_status",
            payload.get("timeline_latest_remediation_execution_plan_status"),
        ),
        "timeline_latest_remediation_execution_plan_next_action_command": payload.get(
            "latest_remediation_execution_plan_next_action_command",
            payload.get("timeline_latest_remediation_execution_plan_next_action_command"),
        ),
        "timeline_latest_remediation_execution_plan_feedback_priority_reason": payload.get(
            "latest_remediation_execution_plan_feedback_priority_reason",
            payload.get("timeline_latest_remediation_execution_plan_feedback_priority_reason"),
        ),
        "timeline_latest_remediation_session_status": payload.get(
            "latest_remediation_session_status",
            payload.get("timeline_latest_remediation_session_status"),
        ),
        "timeline_latest_remediation_session_next_pending_command": payload.get(
            "latest_remediation_session_next_pending_command",
            payload.get("timeline_latest_remediation_session_next_pending_command"),
        ),
        "timeline_latest_remediation_session_feedback_priority_reason": payload.get(
            "latest_remediation_session_feedback_priority_reason",
            payload.get("timeline_latest_remediation_session_feedback_priority_reason"),
        ),
        "timeline_latest_remediation_checkpoint_status": payload.get(
            "latest_remediation_checkpoint_status",
            payload.get("timeline_latest_remediation_checkpoint_status"),
        ),
        "timeline_latest_remediation_checkpoint_next_action_command": payload.get(
            "latest_remediation_checkpoint_next_action_command",
            payload.get("timeline_latest_remediation_checkpoint_next_action_command"),
        ),
        "timeline_latest_remediation_checkpoint_feedback_priority_reason": payload.get(
            "latest_remediation_checkpoint_feedback_priority_reason",
            payload.get("timeline_latest_remediation_checkpoint_feedback_priority_reason"),
        ),
        "timeline_latest_remediation_scoreboard_status": payload.get(
            "latest_remediation_scoreboard_status",
            payload.get("timeline_latest_remediation_scoreboard_status"),
        ),
        "timeline_latest_remediation_scoreboard_next_action_command": payload.get(
            "latest_remediation_scoreboard_next_action_command",
            payload.get("timeline_latest_remediation_scoreboard_next_action_command"),
        ),
        "timeline_latest_remediation_scoreboard_feedback_priority_reason": payload.get(
            "latest_remediation_scoreboard_feedback_priority_reason",
            payload.get("timeline_latest_remediation_scoreboard_feedback_priority_reason"),
        ),
    }


def audit_bundle_history_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return {
        "bundle_history_snapshot_count": payload.get("snapshot_count"),
        "bundle_history_ok_count": payload.get("ok_count"),
        "bundle_history_latest_execution_overall_status": payload.get(
            "latest_execution_overall_status",
            payload.get("bundle_history_latest_execution_overall_status"),
        ),
        "bundle_history_latest_execution_venue_count": payload.get(
            "latest_execution_venue_count",
            payload.get("bundle_history_latest_execution_venue_count"),
        ),
        "bundle_history_latest_execution_comparison_all_registries_present": payload.get(
            "latest_execution_comparison_all_registries_present",
            payload.get("bundle_history_latest_execution_comparison_all_registries_present"),
        ),
        "bundle_history_latest_execution_gap_history_status": payload.get(
            "latest_execution_gap_history_status",
            payload.get("bundle_history_latest_execution_gap_history_status"),
        ),
        "bundle_history_latest_execution_gap_history_diagnostics_status": payload.get(
            "latest_execution_gap_history_diagnostics_status",
            payload.get("bundle_history_latest_execution_gap_history_diagnostics_status"),
        ),
        "bundle_history_latest_readiness_execution_ready": payload.get(
            "latest_readiness_execution_ready",
            payload.get("bundle_history_latest_readiness_execution_ready"),
        ),
    }


def ops_review_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return {
        "ops_operations_count": payload.get("operations_count"),
        "ops_latest_operation": payload.get("latest_operation"),
        "ops_latest_status": payload.get("latest_status"),
        "ops_latest_scheduled_for": payload.get("latest_scheduled_for"),
        "ops_monitoring_status": payload.get("monitoring_status"),
        "ops_daemon_dry_run_status": payload.get("daemon_dry_run_status"),
    }
