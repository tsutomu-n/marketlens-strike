from __future__ import annotations

from pathlib import Path
from typing import cast

from sis.reports.summary_normalizers import phase_gate_issue_note_previews


def reports_dir(operation_chain_path: Path | None) -> Path | None:
    if operation_chain_path is None:
        return None
    base = (
        operation_chain_path.parent.parent
        if operation_chain_path.parent.name == "ops"
        else operation_chain_path.parent
    )
    return base / "reports"


def note_value(notes: list[object], prefix: str) -> str | None:
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return None


def note_counts(items: list[dict[str, object]], prefix: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        notes = item.get("notes", [])
        if not isinstance(notes, list):
            continue
        value = note_value(cast(list[object], notes), prefix)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def note_values(notes: list[object], prefix: str) -> list[str]:
    values: list[str] = []
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            values.append(text.removeprefix(prefix))
    return values


def latest_operation_entry(items: list[dict[str, object]], operation: str) -> dict[str, object]:
    for item in reversed(items):
        if str(item.get("operation")) == operation:
            return item
    return {}


def latest_note_from_operation(
    items: list[dict[str, object]], operation: str, prefix: str
) -> str | None:
    latest = latest_operation_entry(items, operation)
    notes = latest.get("notes", []) if isinstance(latest, dict) else []
    return note_value(cast(list[object], notes), prefix) if isinstance(notes, list) else None


def latest_notes_with_prefix(items: list[dict[str, object]], prefix: str) -> list[object]:
    for item in reversed(items):
        notes = item.get("notes", [])
        if not isinstance(notes, list):
            continue
        notes = cast(list[object], notes)
        if note_value(notes, prefix) is not None:
            return notes
    return []


REMEDIATION_NOTE_FIELDS = (
    (
        "latest_remediation_planner_status",
        "remediation_planner_dry_run",
        "planner_status=",
    ),
    (
        "latest_remediation_planner_next_best_command",
        "remediation_planner_dry_run",
        "next_best_command=",
    ),
    (
        "latest_remediation_planner_feedback_priority_reason",
        "remediation_planner_dry_run",
        "next_feedback_priority_reason=",
    ),
    (
        "latest_remediation_execution_plan_status",
        "remediation_execution_plan_dry_run",
        "execution_plan_status=",
    ),
    (
        "latest_remediation_execution_plan_next_action_command",
        "remediation_execution_plan_dry_run",
        "next_action_command=",
    ),
    (
        "latest_remediation_execution_plan_feedback_priority_reason",
        "remediation_execution_plan_dry_run",
        "next_action_feedback_priority_reason=",
    ),
    (
        "latest_remediation_session_status",
        "remediation_session_dry_run",
        "session_status=",
    ),
    (
        "latest_remediation_session_next_pending_command",
        "remediation_session_dry_run",
        "next_pending_command=",
    ),
    (
        "latest_remediation_session_feedback_priority_reason",
        "remediation_session_dry_run",
        "next_pending_feedback_priority_reason=",
    ),
    (
        "latest_remediation_checkpoint_status",
        "remediation_session_checkpoint",
        "checkpoint_status=",
    ),
    (
        "latest_remediation_checkpoint_next_action_command",
        "remediation_session_checkpoint",
        "next_action_command=",
    ),
    (
        "latest_remediation_checkpoint_feedback_priority_reason",
        "remediation_session_checkpoint",
        "next_action_feedback_priority_reason=",
    ),
    (
        "latest_remediation_scoreboard_status",
        "remediation_scoreboard",
        "scoreboard_status=",
    ),
    (
        "latest_remediation_scoreboard_next_action_command",
        "remediation_scoreboard",
        "next_action_command=",
    ),
    (
        "latest_remediation_scoreboard_feedback_priority_reason",
        "remediation_scoreboard",
        "next_action_feedback_priority_reason=",
    ),
)


def remediation_state(items: list[dict[str, object]]) -> dict[str, str | None]:
    return {
        key: latest_note_from_operation(items, operation, prefix)
        for key, operation, prefix in REMEDIATION_NOTE_FIELDS
    }


def timeline_latest_note_summary(
    *,
    execution_notes: list[object],
    readiness_notes: list[object],
    phase_gate_notes: list[object],
) -> dict[str, object]:
    phase_gate_issues = phase_gate_issue_note_previews(phase_gate_notes)
    return {
        "latest_execution_diagnostics_summary": {
            "execution_diagnostics_status": note_value(
                execution_notes, "execution_diagnostics_status="
            )
        },
        "latest_execution_drift_overview_summary": {
            "execution_drift_overview_status": note_value(
                execution_notes, "execution_drift_overview_status="
            ),
            "execution_drift_overview_diagnostics_alignment_match": note_value(
                execution_notes,
                "execution_drift_overview_diagnostics_alignment_match=",
            ),
            "execution_drift_overview_state_comparison_mismatching_count": note_value(
                execution_notes,
                "execution_drift_overview_state_comparison_mismatching_count=",
            ),
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": note_value(
                execution_notes,
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
            ),
        },
        "latest_execution_gap_history_summary": {
            "execution_gap_history_latest_status": note_value(
                execution_notes, "execution_gap_history_latest_status="
            ),
            "execution_gap_history_latest_diagnostics_status": note_value(
                execution_notes, "execution_gap_history_latest_diagnostics_status="
            ),
        },
        "latest_execution_state_comparison_summary": {
            "execution_state_comparison_latest_status_match": note_value(
                execution_notes, "execution_state_comparison_latest_status_match="
            ),
            "execution_state_comparison_mismatching_count": note_value(
                execution_notes, "execution_state_comparison_mismatching_count="
            ),
        },
        "latest_readiness_summary": {
            "readiness_next_phase_candidate": note_value(readiness_notes, "readiness_next_phase="),
            "readiness_execution_ready": note_value(readiness_notes, "readiness_execution_ready="),
        },
        "latest_phase_gate_summary": {
            "phase_gate_decision": note_value(phase_gate_notes, "phase_gate_decision="),
            "phase2_entry_allowed": note_value(phase_gate_notes, "phase2_entry_allowed="),
            "phase_gate_reason": note_value(phase_gate_notes, "phase_gate_reason="),
            "phase_gate_strict_validation_passed": note_value(
                phase_gate_notes, "phase_gate_strict_validation_passed="
            ),
            "phase_gate_strict_validation_issue_count": note_value(
                phase_gate_notes, "phase_gate_strict_validation_issue_count="
            ),
            "phase_gate_checked_files": note_value(phase_gate_notes, "phase_gate_checked_files="),
            "phase_gate_review_report_path": note_value(
                phase_gate_notes, "phase_gate_review_report_path="
            ),
            "phase_gate_strict_validation_issues": phase_gate_issues,
        },
        "latest_execution_diagnostics_status": note_value(
            execution_notes, "execution_diagnostics_status="
        ),
        "latest_execution_drift_overview_status": note_value(
            execution_notes, "execution_drift_overview_status="
        ),
        "latest_execution_drift_overview_diagnostics_alignment_match": note_value(
            execution_notes,
            "execution_drift_overview_diagnostics_alignment_match=",
        ),
        "latest_execution_drift_overview_state_comparison_mismatching_count": note_value(
            execution_notes,
            "execution_drift_overview_state_comparison_mismatching_count=",
        ),
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": note_value(
            execution_notes,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
        ),
        "latest_execution_gap_history_status": note_value(
            execution_notes, "execution_gap_history_latest_status="
        ),
        "latest_execution_gap_history_diagnostics_status": note_value(
            execution_notes, "execution_gap_history_latest_diagnostics_status="
        ),
        "latest_execution_state_comparison_status_match": note_value(
            execution_notes, "execution_state_comparison_latest_status_match="
        ),
        "latest_execution_state_comparison_mismatching_count": note_value(
            execution_notes, "execution_state_comparison_mismatching_count="
        ),
        "latest_readiness_next_phase": note_value(readiness_notes, "readiness_next_phase="),
        "latest_readiness_execution_ready": note_value(
            readiness_notes, "readiness_execution_ready="
        ),
        "latest_phase_gate_decision": note_value(phase_gate_notes, "phase_gate_decision="),
        "latest_phase2_entry_allowed": note_value(phase_gate_notes, "phase2_entry_allowed="),
        "latest_phase_gate_reason": note_value(phase_gate_notes, "phase_gate_reason="),
        "latest_phase_gate_strict_validation_passed": note_value(
            phase_gate_notes, "phase_gate_strict_validation_passed="
        ),
        "latest_phase_gate_strict_validation_issue_count": note_value(
            phase_gate_notes, "phase_gate_strict_validation_issue_count="
        ),
        "latest_phase_gate_checked_files": note_value(
            phase_gate_notes, "phase_gate_checked_files="
        ),
        "latest_phase_gate_review_report_path": note_value(
            phase_gate_notes, "phase_gate_review_report_path="
        ),
        "latest_phase_gate_issue_previews": phase_gate_issues,
    }
