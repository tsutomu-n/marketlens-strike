from __future__ import annotations


def current_schedule_section_lines(summary: dict[str, object]) -> list[str]:
    return [
        "## Current Schedule",
        "",
        f"- run_type: {summary['scheduled_run_type']}",
        f"- scheduled_for: {summary['scheduled_for']}",
        f"- command: {summary['scheduled_command']}",
    ]


def current_daemon_context_section_lines(
    summary: dict[str, object],
    daemon_manifest: dict[str, object],
) -> list[str]:
    return [
        "## Current Daemon Context",
        "",
        f"- daemon_mode: {summary['daemon_mode']}",
        f"- daemon_command: {daemon_manifest.get('command')}",
        f"- state_store_path: {daemon_manifest.get('state_store_path')}",
        f"- daemon_manifest_path: {summary['daemon_manifest_path']}",
    ]


def current_status_section_lines(summary: dict[str, object]) -> list[str]:
    return [
        "## Current Status",
        "",
        f"- monitoring_status: {summary['monitoring_status']}",
        f"- execution_overall_status: {summary['execution_overall_status']}",
        f"- execution_venue_count: {summary['execution_venue_count']}",
        (
            "- execution_comparison_all_registries_present: "
            f"{summary['execution_comparison_all_registries_present']}"
        ),
        f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
        f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
        f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
        (f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}"),
        (
            "- execution_gap_history_latest_status: "
            f"{summary['execution_gap_history_latest_status']}"
        ),
        (
            "- execution_gap_history_latest_diagnostics_status: "
            f"{summary['execution_gap_history_latest_diagnostics_status']}"
        ),
        (
            "- execution_state_comparison_entry_count: "
            f"{summary['execution_state_comparison_entry_count']}"
        ),
        (
            "- execution_state_comparison_latest_status_match: "
            f"{summary['execution_state_comparison_latest_status_match']}"
        ),
        (
            "- execution_state_comparison_mismatching_count: "
            f"{summary['execution_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_snapshot_drift_entry_count: "
            f"{summary['execution_snapshot_drift_entry_count']}"
        ),
        (
            "- execution_snapshot_drift_latest_status_match: "
            f"{summary['execution_snapshot_drift_latest_status_match']}"
        ),
        (
            "- execution_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['execution_snapshot_drift_mismatching_snapshot_count']}"
        ),
        (f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}"),
        (
            "- execution_drift_overview_diagnostics_alignment_match: "
            f"{summary['execution_drift_overview_diagnostics_alignment_match']}"
        ),
        (
            "- execution_drift_overview_state_comparison_mismatching_count: "
            f"{summary['execution_drift_overview_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
        ),
        (f"- readiness_next_phase_candidate: {summary['readiness_next_phase_candidate']}"),
        f"- readiness_execution_ready: {summary['readiness_execution_ready']}",
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        (
            "- phase_gate_strict_validation_passed: "
            f"{summary['phase_gate_strict_validation_passed']}"
        ),
        (
            "- phase_gate_strict_validation_issue_count: "
            f"{summary['phase_gate_strict_validation_issue_count']}"
        ),
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
        f"- dashboard_status: {summary['dashboard_status']}",
    ]


def current_remediation_queue_section_lines(summary: dict[str, object]) -> list[str]:
    return [
        "## Current Remediation Queue",
        "",
        (
            "- timeline_latest_remediation_planner_status: "
            f"{summary.get('timeline_latest_remediation_planner_status')}"
        ),
        (
            "- timeline_latest_remediation_planner_next_best_command: "
            f"{summary.get('timeline_latest_remediation_planner_next_best_command')}"
        ),
        (
            "- timeline_latest_remediation_planner_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_planner_feedback_priority_reason')}"
        ),
        (
            "- timeline_latest_remediation_execution_plan_status: "
            f"{summary.get('timeline_latest_remediation_execution_plan_status')}"
        ),
        (
            "- timeline_latest_remediation_execution_plan_next_action_command: "
            f"{summary.get('timeline_latest_remediation_execution_plan_next_action_command')}"
        ),
        (
            "- timeline_latest_remediation_execution_plan_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_execution_plan_feedback_priority_reason')}"
        ),
        (
            "- timeline_latest_remediation_session_status: "
            f"{summary.get('timeline_latest_remediation_session_status')}"
        ),
        (
            "- timeline_latest_remediation_session_next_pending_command: "
            f"{summary.get('timeline_latest_remediation_session_next_pending_command')}"
        ),
        (
            "- timeline_latest_remediation_session_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_session_feedback_priority_reason')}"
        ),
        (
            "- timeline_latest_remediation_checkpoint_status: "
            f"{summary.get('timeline_latest_remediation_checkpoint_status')}"
        ),
        (
            "- timeline_latest_remediation_checkpoint_next_action_command: "
            f"{summary.get('timeline_latest_remediation_checkpoint_next_action_command')}"
        ),
        (
            "- timeline_latest_remediation_checkpoint_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_checkpoint_feedback_priority_reason')}"
        ),
        (
            "- timeline_latest_remediation_scoreboard_status: "
            f"{summary.get('timeline_latest_remediation_scoreboard_status')}"
        ),
        (
            "- timeline_latest_remediation_scoreboard_next_action_command: "
            f"{summary.get('timeline_latest_remediation_scoreboard_next_action_command')}"
        ),
        (
            "- timeline_latest_remediation_scoreboard_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_scoreboard_feedback_priority_reason')}"
        ),
    ]
