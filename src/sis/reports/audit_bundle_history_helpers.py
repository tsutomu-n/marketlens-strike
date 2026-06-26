from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import phase_gate_issue_note_previews


def note_value(notes: list[object], prefix: str) -> str | None:
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return None


def note_values(notes: list[object], prefix: str) -> list[str]:
    values: list[str] = []
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            values.append(text.removeprefix(prefix))
    return values


def reports_dir(operation_chain_path: Path | None) -> Path | None:
    if operation_chain_path is None:
        return None
    base = (
        operation_chain_path.parent.parent
        if operation_chain_path.parent.name == "ops"
        else operation_chain_path.parent
    )
    return base / "reports"


def quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("audit_bundle_history_report", summary.get("audit_bundle_history_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def related_reports(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("audit_bundle_history_report", summary.get("audit_bundle_history_report_path")),
        ("audit_timeline_report", summary.get("audit_timeline_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("audit_bundle_report", summary.get("audit_bundle_report_path")),
        ("operations_audit_pack_report", summary.get("operations_audit_pack_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def latest_note_summary_fields(notes: list[object]) -> dict[str, object]:
    latest_remediation_planner_status = note_value(notes, "planner_status=")
    latest_remediation_planner_next_best_command = note_value(notes, "next_best_command=")
    latest_remediation_planner_feedback_priority_reason = note_value(
        notes, "next_feedback_priority_reason="
    )
    latest_remediation_execution_plan_status = note_value(notes, "execution_plan_status=")
    latest_remediation_execution_plan_next_action_command = note_value(
        notes, "next_action_command="
    )
    latest_remediation_execution_plan_feedback_priority_reason = note_value(
        notes, "next_action_feedback_priority_reason="
    )
    latest_remediation_session_status = note_value(notes, "session_status=")
    latest_remediation_session_next_pending_command = note_value(notes, "next_pending_command=")
    latest_remediation_session_feedback_priority_reason = note_value(
        notes, "next_pending_feedback_priority_reason="
    )
    latest_remediation_checkpoint_status = note_value(notes, "checkpoint_status=")
    latest_remediation_checkpoint_next_action_command = note_value(notes, "next_action_command=")
    latest_remediation_checkpoint_feedback_priority_reason = note_value(
        notes, "next_action_feedback_priority_reason="
    )
    latest_remediation_scoreboard_status = note_value(notes, "scoreboard_status=")
    latest_remediation_scoreboard_next_action_command = note_value(notes, "next_action_command=")
    latest_remediation_scoreboard_feedback_priority_reason = note_value(
        notes, "next_action_feedback_priority_reason="
    )
    phase_gate_issue_previews = phase_gate_issue_note_previews(notes)

    return {
        "latest_execution_drift_overview_summary": {
            "execution_drift_overview_status": note_value(
                notes, "execution_drift_overview_status="
            ),
            "execution_drift_overview_diagnostics_alignment_match": note_value(
                notes, "execution_drift_overview_diagnostics_alignment_match="
            ),
            "execution_drift_overview_state_comparison_mismatching_count": note_value(
                notes, "execution_drift_overview_state_comparison_mismatching_count="
            ),
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": note_value(
                notes,
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
            ),
        },
        "latest_execution_gap_history_summary": {
            "execution_gap_history_latest_status": note_value(
                notes, "execution_gap_history_latest_status="
            ),
            "execution_gap_history_latest_diagnostics_status": note_value(
                notes, "execution_gap_history_latest_diagnostics_status="
            ),
        },
        "latest_execution_state_comparison_summary": {
            "execution_state_comparison_latest_status_match": note_value(
                notes, "execution_state_comparison_latest_status_match="
            ),
            "execution_state_comparison_mismatching_count": note_value(
                notes, "execution_state_comparison_mismatching_count="
            ),
        },
        "latest_readiness_summary": {
            "readiness_next_phase_candidate": note_value(notes, "readiness_next_phase="),
            "readiness_execution_ready": note_value(notes, "readiness_execution_ready="),
        },
        "latest_phase_gate_summary": {
            "phase_gate_decision": note_value(notes, "phase_gate_decision="),
            "phase2_entry_allowed": note_value(notes, "phase2_entry_allowed="),
            "phase_gate_reason": note_value(notes, "phase_gate_reason="),
            "phase_gate_strict_validation_passed": note_value(
                notes, "phase_gate_strict_validation_passed="
            ),
            "phase_gate_strict_validation_issue_count": note_value(
                notes, "phase_gate_strict_validation_issue_count="
            ),
            "phase_gate_checked_files": note_value(notes, "phase_gate_checked_files="),
            "phase_gate_review_report_path": note_value(notes, "phase_gate_review_report_path="),
            "phase_gate_strict_validation_issues": phase_gate_issue_previews,
        },
        "latest_execution_gap_history_status": note_value(
            notes, "execution_gap_history_latest_status="
        ),
        "latest_execution_drift_overview_status": note_value(
            notes, "execution_drift_overview_status="
        ),
        "latest_execution_drift_overview_diagnostics_alignment_match": note_value(
            notes, "execution_drift_overview_diagnostics_alignment_match="
        ),
        "latest_execution_drift_overview_state_comparison_mismatching_count": note_value(
            notes, "execution_drift_overview_state_comparison_mismatching_count="
        ),
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": note_value(
            notes,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
        ),
        "latest_execution_gap_history_diagnostics_status": note_value(
            notes, "execution_gap_history_latest_diagnostics_status="
        ),
        "latest_execution_state_comparison_status_match": note_value(
            notes, "execution_state_comparison_latest_status_match="
        ),
        "latest_execution_state_comparison_mismatching_count": note_value(
            notes, "execution_state_comparison_mismatching_count="
        ),
        "latest_readiness_next_phase": note_value(notes, "readiness_next_phase="),
        "latest_readiness_execution_ready": note_value(notes, "readiness_execution_ready="),
        "latest_phase_gate_decision": note_value(notes, "phase_gate_decision="),
        "latest_phase2_entry_allowed": note_value(notes, "phase2_entry_allowed="),
        "latest_phase_gate_reason": note_value(notes, "phase_gate_reason="),
        "latest_phase_gate_strict_validation_passed": note_value(
            notes, "phase_gate_strict_validation_passed="
        ),
        "latest_phase_gate_strict_validation_issue_count": note_value(
            notes, "phase_gate_strict_validation_issue_count="
        ),
        "latest_phase_gate_checked_files": note_value(notes, "phase_gate_checked_files="),
        "latest_phase_gate_review_report_path": note_value(notes, "phase_gate_review_report_path="),
        "latest_phase_gate_issue_previews": phase_gate_issue_previews,
        "latest_remediation_planner_status": latest_remediation_planner_status,
        "latest_remediation_planner_next_best_command": (
            latest_remediation_planner_next_best_command
        ),
        "latest_remediation_planner_feedback_priority_reason": (
            latest_remediation_planner_feedback_priority_reason
        ),
        "latest_remediation_execution_plan_status": (latest_remediation_execution_plan_status),
        "latest_remediation_execution_plan_next_action_command": (
            latest_remediation_execution_plan_next_action_command
        ),
        "latest_remediation_execution_plan_feedback_priority_reason": (
            latest_remediation_execution_plan_feedback_priority_reason
        ),
        "latest_remediation_session_status": latest_remediation_session_status,
        "latest_remediation_session_next_pending_command": (
            latest_remediation_session_next_pending_command
        ),
        "latest_remediation_session_feedback_priority_reason": (
            latest_remediation_session_feedback_priority_reason
        ),
        "latest_remediation_checkpoint_status": latest_remediation_checkpoint_status,
        "latest_remediation_checkpoint_next_action_command": (
            latest_remediation_checkpoint_next_action_command
        ),
        "latest_remediation_checkpoint_feedback_priority_reason": (
            latest_remediation_checkpoint_feedback_priority_reason
        ),
        "latest_remediation_scoreboard_status": latest_remediation_scoreboard_status,
        "latest_remediation_scoreboard_next_action_command": (
            latest_remediation_scoreboard_next_action_command
        ),
        "latest_remediation_scoreboard_feedback_priority_reason": (
            latest_remediation_scoreboard_feedback_priority_reason
        ),
    }
