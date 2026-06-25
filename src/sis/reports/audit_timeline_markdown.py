from __future__ import annotations

from typing import Any, Mapping


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _lines_for_counts(
    *,
    title: str,
    values: Any,
    empty_line: str,
) -> list[str]:
    lines = [title, ""]
    counts = _mapping(values)
    if counts:
        for key in sorted(counts):
            lines.append(f"- {key}: {counts[key]}")
    else:
        lines.append(empty_line)
    lines.append("")
    return lines


def render_audit_timeline_markdown(
    *,
    summary: dict[str, object],
    recent: list[dict[str, object]],
) -> str:
    quick_navigation = _mapping(summary.get("quick_navigation"))
    related_reports = _mapping(summary.get("related_reports"))
    latest_phase_gate_issue_previews = summary.get("latest_phase_gate_issue_previews")
    latest_phase_gate_issue_previews = (
        latest_phase_gate_issue_previews
        if isinstance(latest_phase_gate_issue_previews, list)
        else []
    )
    lines = [
        "# Audit Timeline Report",
        "",
        "## Summary",
        "",
        f"- audit_entry_count: {summary['audit_entry_count']}",
        f"- recent_count: {summary['recent_count']}",
        f"- latest_operation: {summary['latest_operation']}",
        f"- latest_status: {summary['latest_status']}",
        f"- latest_execution_overall_status: {summary['latest_execution_overall_status']}",
        f"- latest_execution_venue_count: {summary['latest_execution_venue_count']}",
        (
            "- latest_execution_comparison_all_registries_present: "
            f"{summary['latest_execution_comparison_all_registries_present']}"
        ),
        f"- latest_execution_diagnostics_status: {summary['latest_execution_diagnostics_status']}",
        f"- latest_execution_drift_overview_status: {summary['latest_execution_drift_overview_status']}",
        (
            "- latest_execution_drift_overview_diagnostics_alignment_match: "
            f"{summary['latest_execution_drift_overview_diagnostics_alignment_match']}"
        ),
        (
            "- latest_execution_drift_overview_state_comparison_mismatching_count: "
            f"{summary['latest_execution_drift_overview_state_comparison_mismatching_count']}"
        ),
        (
            "- latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- latest_execution_gap_history_status: {summary['latest_execution_gap_history_status']}",
        (
            "- latest_execution_gap_history_diagnostics_status: "
            f"{summary['latest_execution_gap_history_diagnostics_status']}"
        ),
        (
            "- latest_execution_state_comparison_status_match: "
            f"{summary['latest_execution_state_comparison_status_match']}"
        ),
        (
            "- latest_execution_state_comparison_mismatching_count: "
            f"{summary['latest_execution_state_comparison_mismatching_count']}"
        ),
        f"- latest_readiness_next_phase: {summary['latest_readiness_next_phase']}",
        f"- latest_readiness_execution_ready: {summary['latest_readiness_execution_ready']}",
        f"- latest_phase_gate_decision: {summary['latest_phase_gate_decision']}",
        f"- latest_phase2_entry_allowed: {summary['latest_phase2_entry_allowed']}",
        f"- latest_phase_gate_reason: {summary['latest_phase_gate_reason']}",
        f"- latest_phase_gate_strict_validation_passed: {summary['latest_phase_gate_strict_validation_passed']}",
        (
            "- latest_phase_gate_strict_validation_issue_count: "
            f"{summary['latest_phase_gate_strict_validation_issue_count']}"
        ),
        f"- latest_phase_gate_checked_files: {summary['latest_phase_gate_checked_files']}",
        f"- latest_phase_gate_review_report_path: {summary['latest_phase_gate_review_report_path']}",
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in related_reports.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Remediation State",
            "",
            f"- latest_remediation_planner_status: {summary['latest_remediation_planner_status']}",
            f"- latest_remediation_planner_next_best_command: {summary['latest_remediation_planner_next_best_command']}",
            f"- latest_remediation_planner_feedback_priority_reason: {summary['latest_remediation_planner_feedback_priority_reason']}",
            f"- latest_remediation_execution_plan_status: {summary['latest_remediation_execution_plan_status']}",
            f"- latest_remediation_execution_plan_next_action_command: {summary['latest_remediation_execution_plan_next_action_command']}",
            f"- latest_remediation_execution_plan_feedback_priority_reason: {summary['latest_remediation_execution_plan_feedback_priority_reason']}",
            f"- latest_remediation_session_status: {summary['latest_remediation_session_status']}",
            f"- latest_remediation_session_next_pending_command: {summary['latest_remediation_session_next_pending_command']}",
            f"- latest_remediation_session_feedback_priority_reason: {summary['latest_remediation_session_feedback_priority_reason']}",
            f"- latest_remediation_checkpoint_status: {summary['latest_remediation_checkpoint_status']}",
            f"- latest_remediation_checkpoint_next_action_command: {summary['latest_remediation_checkpoint_next_action_command']}",
            f"- latest_remediation_checkpoint_feedback_priority_reason: {summary['latest_remediation_checkpoint_feedback_priority_reason']}",
            f"- latest_remediation_scoreboard_status: {summary['latest_remediation_scoreboard_status']}",
            f"- latest_remediation_scoreboard_next_action_command: {summary['latest_remediation_scoreboard_next_action_command']}",
            f"- latest_remediation_scoreboard_feedback_priority_reason: {summary['latest_remediation_scoreboard_feedback_priority_reason']}",
            "",
            "## Audit Entry Counts",
            "",
        ]
    )
    if latest_phase_gate_issue_previews:
        lines.extend(["## Latest Phase Gate Issue Preview", ""])
        lines.extend(f"- {item}" for item in latest_phase_gate_issue_previews)
        lines.append("")
    audit_counts = _mapping(summary.get("operation_counts"))
    if audit_counts:
        for key in sorted(audit_counts):
            lines.append(f"- {key}: {audit_counts[key]}")
    else:
        lines.append("- no audit snapshot entries were available")
    lines.append("")

    count_sections = [
        (
            "## Diagnostics Status Counts",
            "diagnostics_status_counts",
            "- no execution diagnostics notes were available",
        ),
        (
            "## Drift Overview Status Counts",
            "drift_overview_status_counts",
            "- no execution drift overview notes were available",
        ),
        (
            "## Drift Overview Diagnostics Alignment Counts",
            "drift_overview_diagnostics_alignment_counts",
            "- no execution drift overview alignment notes were available",
        ),
        (
            "## Drift Overview State Comparison Mismatching Count Values",
            "drift_overview_state_comparison_mismatching_count_values",
            "- no execution drift overview state comparison mismatch notes were available",
        ),
        (
            "## Drift Overview Snapshot Drift Mismatching Count Values",
            "drift_overview_snapshot_drift_mismatching_snapshot_count_values",
            "- no execution drift overview snapshot drift mismatch notes were available",
        ),
        (
            "## Gap History Status Counts",
            "gap_history_status_counts",
            "- no execution gap history status notes were available",
        ),
        (
            "## Gap History Diagnostics Status Counts",
            "gap_history_diagnostics_status_counts",
            "- no execution gap history diagnostics notes were available",
        ),
        (
            "## State Comparison Status Match Counts",
            "state_comparison_status_match_counts",
            "- no execution state comparison match notes were available",
        ),
        (
            "## State Comparison Mismatching Count Values",
            "state_comparison_mismatching_count_values",
            "- no execution state comparison mismatch notes were available",
        ),
        (
            "## Readiness Next Phase Counts",
            "readiness_next_phase_counts",
            "- no readiness notes were available",
        ),
        (
            "## Readiness Execution Ready Counts",
            "readiness_execution_ready_counts",
            "- no readiness execution-ready notes were available",
        ),
        (
            "## Phase Gate Decision Counts",
            "phase_gate_decision_counts",
            "- no phase gate decision notes were available",
        ),
        (
            "## Phase 2 Entry Allowed Counts",
            "phase2_entry_allowed_counts",
            "- no phase2 entry notes were available",
        ),
        (
            "## Phase Gate Reason Counts",
            "phase_gate_reason_counts",
            "- no phase gate reason notes were available",
        ),
        (
            "## Phase Gate Strict Validation Counts",
            "phase_gate_strict_validation_passed_counts",
            "- no phase gate strict validation notes were available",
        ),
        (
            "## Phase Gate Strict Validation Issue Count Values",
            "phase_gate_strict_validation_issue_count_values",
            "- no phase gate strict validation issue count notes were available",
        ),
        (
            "## Phase Gate Checked Files Values",
            "phase_gate_checked_files_values",
            "- no phase gate checked files notes were available",
        ),
    ]
    for title, key, empty_line in count_sections:
        lines.extend(
            _lines_for_counts(
                title=title,
                values=summary.get(key),
                empty_line=empty_line,
            )
        )

    lines.extend(["## Recent Audit Timeline", ""])
    if recent:
        for item in recent:
            notes = item.get("notes", [])
            notes_text = ", ".join(str(x) for x in notes) if isinstance(notes, list) else ""
            lines.append(
                f"- {item.get('created_at')} | op={item.get('operation')} | status={item.get('status')} | notes={notes_text}"
            )
    else:
        lines.append("- no audit timeline entries available")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
