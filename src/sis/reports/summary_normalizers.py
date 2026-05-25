from __future__ import annotations

from typing import Any, Mapping, Sequence


_SOURCE_QUALITY_RANKS = {
    "observed_signals": 0,
    "stdout_stderr": 0,
    "exit_code": 0,
    "live_evidence_summary": 1,
    "current_state_index": 1,
    "ops_review": 1,
    "dashboard_bundle": 1,
    "timeline_summary": 1,
    "phase_gate_review": 1,
    "paper_operations_runbook": 1,
    "manifest_notes": 2,
    "markdown_reports": 2,
}


def _normalize_bool_like(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return value


def normalize_phase_gate_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    reason = payload.get("phase_gate_reason") or payload.get("phase2_entry_reason")
    strict_validation = (
        payload.get("phase_gate_strict_validation_passed")
        if payload.get("phase_gate_strict_validation_passed") is not None
        else payload.get("strict_validation_passed")
    )
    strict_validation_issue_count = (
        payload.get("phase_gate_strict_validation_issue_count")
        if payload.get("phase_gate_strict_validation_issue_count") is not None
        else payload.get("strict_validation_issue_count")
    )
    checked_files = (
        payload.get("phase_gate_checked_files")
        if payload.get("phase_gate_checked_files") is not None
        else payload.get("checked_files")
    )
    strict_validation_issues = payload.get("phase_gate_strict_validation_issues")
    if strict_validation_issues is None:
        strict_validation_issues = payload.get("strict_validation_issues")
    report_path = payload.get("phase_gate_review_report_path")
    return {
        **payload,
        "decision": payload.get("decision") or payload.get("phase_gate_decision"),
        "phase2_entry_reason": payload.get("phase2_entry_reason") or reason,
        "phase_gate_reason": reason,
        "phase_gate_strict_validation_passed": strict_validation,
        "phase_gate_strict_validation_issue_count": strict_validation_issue_count,
        "phase_gate_checked_files": checked_files,
        "strict_validation_issue_count": strict_validation_issue_count,
        "checked_files": checked_files,
        "phase_gate_strict_validation_issues": strict_validation_issues,
        "strict_validation_issues": strict_validation_issues,
        "phase_gate_review_report_path": report_path,
        "strict_validation_passed": strict_validation,
    }


def normalize_readiness_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    next_phase_candidate = payload.get("next_phase_candidate") or payload.get("readiness_next_phase_candidate")
    execution_ready = (
        payload.get("execution_ready")
        if payload.get("execution_ready") is not None
        else payload.get("readiness_execution_ready")
    )
    return {
        **payload,
        "next_phase_candidate": next_phase_candidate,
        "execution_ready": execution_ready,
        "readiness_next_phase_candidate": next_phase_candidate,
        "readiness_execution_ready": execution_ready,
    }


def normalize_execution_drift_overview_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    overall_status = payload.get("overall_status") or payload.get("execution_drift_overview_status")
    diagnostics_alignment_match = (
        payload.get("diagnostics_alignment_match")
        if payload.get("diagnostics_alignment_match") is not None
        else payload.get("execution_drift_overview_diagnostics_alignment_match")
    )
    state_comparison_mismatching_count = (
        payload.get("state_comparison_mismatching_count")
        if payload.get("state_comparison_mismatching_count") is not None
        else payload.get("execution_drift_overview_state_comparison_mismatching_count")
    )
    snapshot_drift_mismatching_snapshot_count = (
        payload.get("snapshot_drift_mismatching_snapshot_count")
        if payload.get("snapshot_drift_mismatching_snapshot_count") is not None
        else payload.get("execution_drift_overview_snapshot_drift_mismatching_snapshot_count")
    )
    return {
        **payload,
        "overall_status": overall_status,
        "diagnostics_alignment_match": diagnostics_alignment_match,
        "state_comparison_mismatching_count": state_comparison_mismatching_count,
        "snapshot_drift_mismatching_snapshot_count": snapshot_drift_mismatching_snapshot_count,
        "execution_drift_overview_status": overall_status,
        "execution_drift_overview_diagnostics_alignment_match": diagnostics_alignment_match,
        "execution_drift_overview_state_comparison_mismatching_count": state_comparison_mismatching_count,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            snapshot_drift_mismatching_snapshot_count
        ),
    }


def phase_gate_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_phase_gate_summary(summary)
    return {
        "phase_gate_decision": payload.get("decision"),
        "phase2_entry_allowed": payload.get("phase2_entry_allowed"),
        "phase2_entry_reason": payload.get("phase2_entry_reason"),
        "phase_gate_reason": payload.get("phase_gate_reason"),
        "phase_gate_strict_validation_passed": payload.get("phase_gate_strict_validation_passed"),
        "phase_gate_strict_validation_issue_count": payload.get(
            "phase_gate_strict_validation_issue_count"
        ),
        "phase_gate_checked_files": payload.get("phase_gate_checked_files"),
        "phase_gate_strict_validation_issues": payload.get("phase_gate_strict_validation_issues"),
        "phase_gate_review_report_path": payload.get("phase_gate_review_report_path"),
        "strict_validation_passed": payload.get("strict_validation_passed"),
    }


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
    bundle_history_snapshot_count = audit_bundle_fields.get(
        "audit_bundle_history_snapshot_count"
    )
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


def phase_gate_nested_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_phase_gate_summary(summary)
    return {
        "decision": payload.get("decision"),
        "phase2_entry_allowed": payload.get("phase2_entry_allowed"),
        "phase2_entry_reason": payload.get("phase2_entry_reason"),
        "phase_gate_reason": payload.get("phase_gate_reason"),
        "phase_gate_strict_validation_passed": payload.get("phase_gate_strict_validation_passed"),
        "phase_gate_strict_validation_issue_count": payload.get("phase_gate_strict_validation_issue_count"),
        "phase_gate_checked_files": payload.get("phase_gate_checked_files"),
        "phase_gate_strict_validation_issues": payload.get("phase_gate_strict_validation_issues"),
        "phase_gate_review_report_path": payload.get("phase_gate_review_report_path"),
        "strict_validation_issue_count": payload.get("strict_validation_issue_count"),
        "checked_files": payload.get("checked_files"),
        "strict_validation_issues": payload.get("strict_validation_issues"),
        "strict_validation_passed": payload.get("strict_validation_passed"),
    }


def phase_gate_issue_preview_lines(summary: Mapping[str, Any] | None) -> list[str]:
    payload = normalize_phase_gate_summary(summary)
    issues = payload.get("phase_gate_strict_validation_issues")
    if not isinstance(issues, list):
        return []
    previews: list[str] = []
    for issue in issues:
        if isinstance(issue, dict):
            path = issue.get("path")
            message = issue.get("message")
            if path and message:
                previews.append(f"{path}: {message}")
            elif path:
                previews.append(str(path))
            elif message:
                previews.append(str(message))
        elif isinstance(issue, str):
            previews.append(issue)
    return previews


def phase_gate_issue_note_previews(notes: list[object]) -> list[str]:
    previews: list[str] = []
    for item in notes:
        text = str(item)
        if text.startswith("phase_gate_issue_") and "=" in text:
            previews.append(text.split("=", 1)[1])
    return previews


def phase_gate_issue_note_lines(summary: Mapping[str, Any] | None) -> list[str]:
    previews = phase_gate_issue_preview_lines(summary)
    if not previews:
        return ["phase_gate_issues=none"]
    return [
        f"phase_gate_issue_{index}={preview}"
        for index, preview in enumerate(previews, start=1)
    ]


def readiness_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_readiness_summary(summary)
    return {
        "readiness_next_phase_candidate": payload.get("readiness_next_phase_candidate"),
        "readiness_execution_ready": payload.get("readiness_execution_ready"),
    }


def execution_drift_overview_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_drift_overview_summary(summary)
    return {
        "execution_drift_overview_status": payload.get("execution_drift_overview_status"),
        "execution_drift_overview_diagnostics_alignment_match": payload.get(
            "execution_drift_overview_diagnostics_alignment_match"
        ),
        "execution_drift_overview_state_comparison_mismatching_count": payload.get(
            "execution_drift_overview_state_comparison_mismatching_count"
        ),
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": payload.get(
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        ),
        "execution_drift_overview_report_path": payload.get("report_path"),
    }


def execution_snapshot_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_snapshot_summary(summary)
    return {
        "execution_overall_status": payload.get("overall_status"),
        "execution_venue_count": payload.get("venue_count"),
        "execution_report_path": payload.get("report_path"),
    }


def execution_comparison_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_comparison_summary(summary)
    return {
        "execution_comparison_all_registries_present": payload.get("all_registries_present"),
        "execution_comparison_report_path": payload.get("report_path"),
    }


def execution_diagnostics_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_diagnostics_summary(summary)
    return {
        "execution_diagnostics_status": payload.get("overall_status"),
        "execution_balance_gap_detected": payload.get("balance_gap_detected"),
        "execution_fills_gap_detected": payload.get("fills_gap_detected"),
        "execution_diagnostics_report_path": payload.get("report_path"),
    }


def normalize_execution_snapshot_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    overall_status = payload.get("overall_status") or payload.get("execution_overall_status")
    venue_count = (
        payload.get("venue_count")
        if payload.get("venue_count") is not None
        else payload.get("execution_venue_count")
    )
    report_path = payload.get("report_path") or payload.get("execution_report_path")
    return {
        **payload,
        "overall_status": overall_status,
        "venue_count": venue_count,
        "report_path": report_path,
        "execution_overall_status": overall_status,
        "execution_venue_count": venue_count,
        "execution_report_path": report_path,
    }


def normalize_execution_comparison_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    all_registries_present = (
        payload.get("all_registries_present")
        if payload.get("all_registries_present") is not None
        else payload.get("execution_comparison_all_registries_present")
    )
    all_registries_present = _normalize_bool_like(all_registries_present)
    report_path = payload.get("report_path") or payload.get("execution_comparison_report_path")
    return {
        **payload,
        "all_registries_present": all_registries_present,
        "report_path": report_path,
        "execution_comparison_all_registries_present": all_registries_present,
        "execution_comparison_report_path": report_path,
    }


def latest_execution_lineage_fields(
    summary: Mapping[str, Any] | None,
    *,
    prefix: str,
) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    execution_summary = normalize_execution_snapshot_summary(
        payload.get(f"{prefix}_execution_summary")
    )
    execution_comparison_summary = normalize_execution_comparison_summary(
        payload.get(f"{prefix}_execution_comparison_summary")
    )
    execution_fields = execution_snapshot_flat_fields(execution_summary)
    execution_comparison_fields = execution_comparison_flat_fields(
        execution_comparison_summary
    )
    return {
        f"{prefix}_execution_summary": execution_summary,
        f"{prefix}_execution_comparison_summary": execution_comparison_summary,
        f"{prefix}_execution_overall_status": execution_fields.get(
            "execution_overall_status"
        ),
        f"{prefix}_execution_venue_count": execution_fields.get("execution_venue_count"),
        f"{prefix}_execution_comparison_all_registries_present": (
            execution_comparison_fields.get(
                "execution_comparison_all_registries_present"
            )
        ),
    }


def latest_execution_section_lines(
    title: str,
    execution_summary: Mapping[str, Any] | None,
    execution_comparison_summary: Mapping[str, Any] | None,
) -> list[str]:
    normalized_execution_summary = normalize_execution_snapshot_summary(
        execution_summary
    )
    if not normalized_execution_summary or not any(normalized_execution_summary.values()):
        return []
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary
    )
    execution_flat = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    return [
        title,
        "",
        f"- overall_status: {execution_flat.get('execution_overall_status') or ''}",
        f"- venue_count: {execution_flat.get('execution_venue_count')}",
        (
            "- all_registries_present: "
            f"{execution_comparison_flat.get('execution_comparison_all_registries_present')}"
        ),
        "",
    ]


def latest_execution_sections(
    sections: Sequence[
        tuple[
            str,
            Mapping[str, Any] | None,
            Mapping[str, Any] | None,
        ]
    ],
) -> list[str]:
    lines: list[str] = []
    for title, execution_summary, execution_comparison_summary in sections:
        lines.extend(
            latest_execution_section_lines(
                title,
                execution_summary,
                execution_comparison_summary,
            )
        )
    return lines


def latest_execution_flat_section_lines(
    title: str,
    *,
    overall_status: Any,
    venue_count: Any,
    all_registries_present: Any,
) -> list[str]:
    if overall_status is None and venue_count is None and all_registries_present is None:
        return []
    return [
        title,
        "",
        f"- overall_status: {overall_status or ''}",
        f"- venue_count: {venue_count}",
        f"- all_registries_present: {all_registries_present}",
        "",
    ]


def latest_execution_flat_sections(
    sections: Sequence[tuple[str, Any, Any, Any]],
) -> list[str]:
    lines: list[str] = []
    for title, overall_status, venue_count, all_registries_present in sections:
        lines.extend(
            latest_execution_flat_section_lines(
                title,
                overall_status=overall_status,
                venue_count=venue_count,
                all_registries_present=all_registries_present,
            )
        )
    return lines


def latest_execution_flat_lines(
    *,
    overall_status: Any,
    venue_count: Any,
    all_registries_present: Any,
    overall_status_label: str = "overall_status",
    venue_count_label: str = "venue_count",
    all_registries_present_label: str = "all_registries_present",
) -> list[str]:
    if overall_status is None and venue_count is None and all_registries_present is None:
        return []
    return [
        f"- {overall_status_label}: {overall_status or ''}",
        f"- {venue_count_label}: {venue_count}",
        f"- {all_registries_present_label}: {all_registries_present}",
    ]


def latest_execution_lineage_flat_lines(
    summary: Mapping[str, Any] | None,
) -> list[str]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return [
        (
            "- timeline_latest_execution_overall_status: "
            f"{payload.get('timeline_latest_execution_overall_status')}"
        ),
        (
            "- timeline_latest_execution_venue_count: "
            f"{payload.get('timeline_latest_execution_venue_count')}"
        ),
        (
            "- timeline_latest_execution_comparison_all_registries_present: "
            f"{payload.get('timeline_latest_execution_comparison_all_registries_present')}"
        ),
        (
            "- bundle_history_latest_execution_overall_status: "
            f"{payload.get('bundle_history_latest_execution_overall_status')}"
        ),
        (
            "- bundle_history_latest_execution_venue_count: "
            f"{payload.get('bundle_history_latest_execution_venue_count')}"
        ),
        (
            "- bundle_history_latest_execution_comparison_all_registries_present: "
            f"{payload.get('bundle_history_latest_execution_comparison_all_registries_present')}"
        ),
        (
            "- cycle_history_latest_execution_overall_status: "
            f"{payload.get('cycle_history_latest_execution_overall_status')}"
        ),
        (
            "- cycle_history_latest_execution_venue_count: "
            f"{payload.get('cycle_history_latest_execution_venue_count')}"
        ),
        (
            "- cycle_history_latest_execution_comparison_all_registries_present: "
            f"{payload.get('cycle_history_latest_execution_comparison_all_registries_present')}"
        ),
    ]


def latest_execution_lineage_from_values(
    *,
    prefix: str,
    overall_status: Any,
    venue_count: Any,
    all_registries_present: Any,
) -> dict[str, Any]:
    return latest_execution_lineage_fields(
        {
            f"{prefix}_execution_summary": {
                "overall_status": overall_status,
                "venue_count": venue_count,
            },
            f"{prefix}_execution_comparison_summary": {
                "all_registries_present": all_registries_present,
            },
        },
        prefix=prefix,
    )


def latest_execution_lineage_from_notes(
    notes: Sequence[object] | None,
    *,
    prefix: str = "latest",
) -> dict[str, Any]:
    note_list = list(notes) if isinstance(notes, Sequence) else []

    def _note_value(note_prefix: str) -> str | None:
        for item in note_list:
            text = str(item)
            if text.startswith(note_prefix):
                return text.removeprefix(note_prefix)
        return None

    return latest_execution_lineage_from_values(
        prefix=prefix,
        overall_status=_note_value("execution_overall_status="),
        venue_count=_note_value("execution_venue_count="),
        all_registries_present=_note_value(
            "execution_comparison_all_registries_present="
        ),
    )


def latest_execution_lineage_payload(
    *,
    timeline_latest_execution_summary: Mapping[str, Any] | None = None,
    timeline_latest_execution_comparison_summary: Mapping[str, Any] | None = None,
    bundle_history_latest_execution_summary: Mapping[str, Any] | None = None,
    bundle_history_latest_execution_comparison_summary: Mapping[str, Any] | None = None,
    cycle_history_latest_execution_summary: Mapping[str, Any] | None = None,
    cycle_history_latest_execution_comparison_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "timeline_latest_execution_summary": timeline_latest_execution_summary,
        "timeline_latest_execution_comparison_summary": (
            timeline_latest_execution_comparison_summary
        ),
        "bundle_history_latest_execution_summary": (
            bundle_history_latest_execution_summary
        ),
        "bundle_history_latest_execution_comparison_summary": (
            bundle_history_latest_execution_comparison_summary
        ),
        "cycle_history_latest_execution_summary": cycle_history_latest_execution_summary,
        "cycle_history_latest_execution_comparison_summary": (
            cycle_history_latest_execution_comparison_summary
        ),
    }


def latest_execution_lineage_payload_from_summary(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return latest_execution_lineage_payload(
        timeline_latest_execution_summary=payload.get(
            "timeline_latest_execution_summary"
        ),
        timeline_latest_execution_comparison_summary=payload.get(
            "timeline_latest_execution_comparison_summary"
        ),
        bundle_history_latest_execution_summary=payload.get(
            "bundle_history_latest_execution_summary"
        ),
        bundle_history_latest_execution_comparison_summary=payload.get(
            "bundle_history_latest_execution_comparison_summary"
        ),
        cycle_history_latest_execution_summary=payload.get(
            "cycle_history_latest_execution_summary"
        ),
        cycle_history_latest_execution_comparison_summary=payload.get(
            "cycle_history_latest_execution_comparison_summary"
        ),
    )


def latest_execution_lineage_fields_from_payload(
    *,
    timeline_latest_execution_summary: Mapping[str, Any] | None = None,
    timeline_latest_execution_comparison_summary: Mapping[str, Any] | None = None,
    bundle_history_latest_execution_summary: Mapping[str, Any] | None = None,
    bundle_history_latest_execution_comparison_summary: Mapping[str, Any] | None = None,
    cycle_history_latest_execution_summary: Mapping[str, Any] | None = None,
    cycle_history_latest_execution_comparison_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return all_latest_execution_lineage_fields(
        latest_execution_lineage_payload(
            timeline_latest_execution_summary=timeline_latest_execution_summary,
            timeline_latest_execution_comparison_summary=(
                timeline_latest_execution_comparison_summary
            ),
            bundle_history_latest_execution_summary=(
                bundle_history_latest_execution_summary
            ),
            bundle_history_latest_execution_comparison_summary=(
                bundle_history_latest_execution_comparison_summary
            ),
            cycle_history_latest_execution_summary=cycle_history_latest_execution_summary,
            cycle_history_latest_execution_comparison_summary=(
                cycle_history_latest_execution_comparison_summary
            ),
        )
    )


def latest_execution_lineage_fields_from_summary(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return all_latest_execution_lineage_fields(
        latest_execution_lineage_payload_from_summary(summary)
    )


def latest_execution_payload_and_fields_from_summary(
    summary: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = latest_execution_lineage_payload_from_summary(summary)
    fields = all_latest_execution_lineage_fields(payload)
    return payload, fields


def all_latest_execution_lineage_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    lineages: dict[str, Any] = {}
    for prefix in (
        "timeline_latest",
        "bundle_history_latest",
        "cycle_history_latest",
    ):
        has_source = (
            payload.get(f"{prefix}_execution_summary") not in (None, {})
            or payload.get(f"{prefix}_execution_comparison_summary") not in (None, {})
            or payload.get(f"{prefix}_execution_overall_status") is not None
            or payload.get(f"{prefix}_execution_venue_count") is not None
            or payload.get(f"{prefix}_execution_comparison_all_registries_present")
            is not None
        )
        if has_source:
            lineages.update(latest_execution_lineage_fields(payload, prefix=prefix))
    return lineages


def defaulted_all_latest_execution_lineage_fields(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "timeline_latest_execution_summary": {},
        "timeline_latest_execution_comparison_summary": {},
        "bundle_history_latest_execution_summary": {},
        "bundle_history_latest_execution_comparison_summary": {},
        "cycle_history_latest_execution_summary": {},
        "cycle_history_latest_execution_comparison_summary": {},
        **all_latest_execution_lineage_fields(summary),
    }


def merged_latest_execution_lineage_fields(
    *summaries: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for summary in summaries:
        merged.update(all_latest_execution_lineage_fields(summary))
    return merged


def merged_latest_execution_payload_and_fields(
    *summaries: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = merged_latest_execution_lineage_fields(*summaries)
    payload = latest_execution_lineage_payload_from_summary(fields)
    return payload, fields


def remap_latest_execution_lineage_fields(
    summary: Mapping[str, Any] | None,
    *,
    target_prefix: str,
) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return latest_execution_lineage_fields(
        {
            f"{target_prefix}_execution_summary": payload.get("latest_execution_summary"),
            f"{target_prefix}_execution_comparison_summary": payload.get(
                "latest_execution_comparison_summary"
            ),
        },
        prefix=target_prefix,
    )


def merged_remapped_latest_execution_lineage_fields(
    *items: tuple[Mapping[str, Any] | None, str],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for summary, target_prefix in items:
        merged.update(
            remap_latest_execution_lineage_fields(summary, target_prefix=target_prefix)
        )
    return merged


def first_remapped_latest_execution_lineage_fields(
    *items: tuple[Mapping[str, Any] | None, str],
) -> dict[str, Any]:
    for summary, target_prefix in items:
        payload = dict(summary) if isinstance(summary, Mapping) else {}
        if payload.get("latest_execution_summary") not in (None, {}):
            return remap_latest_execution_lineage_fields(
                payload,
                target_prefix=target_prefix,
            )
    if not items:
        return {}
    summary, target_prefix = items[-1]
    return remap_latest_execution_lineage_fields(summary, target_prefix=target_prefix)


def normalize_execution_diagnostics_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    overall_status = payload.get("overall_status") or payload.get("execution_diagnostics_status")
    balance_gap_detected = (
        payload.get("balance_gap_detected")
        if payload.get("balance_gap_detected") is not None
        else payload.get("execution_balance_gap_detected")
    )
    fills_gap_detected = (
        payload.get("fills_gap_detected")
        if payload.get("fills_gap_detected") is not None
        else payload.get("execution_fills_gap_detected")
    )
    report_path = payload.get("report_path") or payload.get("execution_diagnostics_report_path")
    return {
        **payload,
        "overall_status": overall_status,
        "balance_gap_detected": balance_gap_detected,
        "fills_gap_detected": fills_gap_detected,
        "report_path": report_path,
        "execution_diagnostics_status": overall_status,
        "execution_balance_gap_detected": balance_gap_detected,
        "execution_fills_gap_detected": fills_gap_detected,
        "execution_diagnostics_report_path": report_path,
    }


def execution_gap_history_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_gap_history_summary(summary)
    return {
        "execution_gap_history_entry_count": payload.get("entry_count"),
        "execution_gap_history_latest_status": payload.get("latest_status"),
        "execution_gap_history_latest_diagnostics_status": payload.get(
            "latest_execution_diagnostics_status"
        ),
        "execution_gap_history_report_path": payload.get("report_path"),
    }


def execution_state_comparison_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_state_comparison_summary(summary)
    return {
        "execution_state_comparison_entry_count": payload.get("entry_count"),
        "execution_state_comparison_latest_status": payload.get("latest_status"),
        "execution_state_comparison_latest_diagnostics_status": payload.get(
            "latest_execution_diagnostics_status"
        ),
        "execution_state_comparison_latest_status_match": payload.get("latest_status_match"),
        "execution_state_comparison_mismatching_count": payload.get("mismatching_count"),
        "execution_state_comparison_report_path": payload.get("report_path"),
    }


def execution_snapshot_drift_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_snapshot_drift_summary(summary)
    return {
        "execution_snapshot_drift_entry_count": payload.get("entry_count"),
        "execution_snapshot_drift_latest_status": payload.get("latest_status"),
        "execution_snapshot_drift_latest_diagnostics_status": payload.get(
            "latest_execution_diagnostics_status"
        ),
        "execution_snapshot_drift_latest_status_match": payload.get(
            "latest_execution_state_comparison_status_match"
        )
        if payload.get("latest_execution_state_comparison_status_match") is not None
        else payload.get("latest_status_match"),
        "execution_snapshot_drift_latest_mismatching_count": payload.get(
            "latest_execution_state_comparison_mismatching_count"
        )
        if payload.get("latest_execution_state_comparison_mismatching_count") is not None
        else payload.get("latest_mismatching_count"),
        "execution_snapshot_drift_mismatching_snapshot_count": payload.get(
            "mismatching_snapshot_count"
        ),
        "execution_snapshot_drift_report_path": payload.get("report_path"),
    }


def normalize_execution_gap_history_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    entry_count = (
        payload.get("entry_count")
        if payload.get("entry_count") is not None
        else payload.get("execution_gap_history_entry_count")
    )
    latest_status = payload.get("latest_status") or payload.get("execution_gap_history_latest_status")
    latest_execution_diagnostics_status = payload.get("latest_execution_diagnostics_status") or payload.get(
        "execution_gap_history_latest_diagnostics_status"
    )
    report_path = payload.get("report_path") or payload.get("execution_gap_history_report_path")
    return {
        **payload,
        "entry_count": entry_count,
        "latest_status": latest_status,
        "latest_execution_diagnostics_status": latest_execution_diagnostics_status,
        "report_path": report_path,
        "execution_gap_history_entry_count": entry_count,
        "execution_gap_history_latest_status": latest_status,
        "execution_gap_history_latest_diagnostics_status": latest_execution_diagnostics_status,
        "execution_gap_history_report_path": report_path,
    }


def normalize_execution_state_comparison_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    entry_count = (
        payload.get("entry_count")
        if payload.get("entry_count") is not None
        else payload.get("execution_state_comparison_entry_count")
    )
    latest_status = payload.get("latest_status") or payload.get("execution_state_comparison_latest_status")
    latest_execution_diagnostics_status = payload.get("latest_execution_diagnostics_status") or payload.get(
        "execution_state_comparison_latest_diagnostics_status"
    )
    latest_status_match = (
        payload.get("latest_status_match")
        if payload.get("latest_status_match") is not None
        else payload.get("execution_state_comparison_latest_status_match")
    )
    mismatching_count = (
        payload.get("mismatching_count")
        if payload.get("mismatching_count") is not None
        else payload.get("execution_state_comparison_mismatching_count")
    )
    report_path = payload.get("report_path") or payload.get("execution_state_comparison_report_path")
    return {
        **payload,
        "entry_count": entry_count,
        "latest_status": latest_status,
        "latest_execution_diagnostics_status": latest_execution_diagnostics_status,
        "latest_status_match": latest_status_match,
        "mismatching_count": mismatching_count,
        "report_path": report_path,
        "execution_state_comparison_entry_count": entry_count,
        "execution_state_comparison_latest_status": latest_status,
        "execution_state_comparison_latest_diagnostics_status": latest_execution_diagnostics_status,
        "execution_state_comparison_latest_status_match": latest_status_match,
        "execution_state_comparison_mismatching_count": mismatching_count,
        "execution_state_comparison_report_path": report_path,
    }


def normalize_execution_snapshot_drift_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    entry_count = (
        payload.get("entry_count")
        if payload.get("entry_count") is not None
        else payload.get("execution_snapshot_drift_entry_count")
    )
    latest_status = payload.get("latest_status") or payload.get("execution_snapshot_drift_latest_status")
    latest_execution_diagnostics_status = payload.get("latest_execution_diagnostics_status") or payload.get(
        "execution_snapshot_drift_latest_diagnostics_status"
    )
    latest_status_match = (
        payload.get("latest_execution_state_comparison_status_match")
        if payload.get("latest_execution_state_comparison_status_match") is not None
        else payload.get("execution_snapshot_drift_latest_status_match")
        if payload.get("execution_snapshot_drift_latest_status_match") is not None
        else payload.get("latest_status_match")
    )
    latest_mismatching_count = (
        payload.get("latest_execution_state_comparison_mismatching_count")
        if payload.get("latest_execution_state_comparison_mismatching_count") is not None
        else payload.get("execution_snapshot_drift_latest_mismatching_count")
        if payload.get("execution_snapshot_drift_latest_mismatching_count") is not None
        else payload.get("latest_mismatching_count")
    )
    mismatching_snapshot_count = (
        payload.get("mismatching_snapshot_count")
        if payload.get("mismatching_snapshot_count") is not None
        else payload.get("execution_snapshot_drift_mismatching_snapshot_count")
    )
    report_path = payload.get("report_path") or payload.get("execution_snapshot_drift_report_path")
    return {
        **payload,
        "entry_count": entry_count,
        "latest_status": latest_status,
        "latest_execution_diagnostics_status": latest_execution_diagnostics_status,
        "latest_execution_state_comparison_status_match": latest_status_match,
        "latest_status_match": latest_status_match,
        "latest_execution_state_comparison_mismatching_count": latest_mismatching_count,
        "latest_mismatching_count": latest_mismatching_count,
        "mismatching_snapshot_count": mismatching_snapshot_count,
        "report_path": report_path,
        "execution_snapshot_drift_entry_count": entry_count,
        "execution_snapshot_drift_latest_status": latest_status,
        "execution_snapshot_drift_latest_diagnostics_status": latest_execution_diagnostics_status,
        "execution_snapshot_drift_latest_status_match": latest_status_match,
        "execution_snapshot_drift_latest_mismatching_count": latest_mismatching_count,
        "execution_snapshot_drift_mismatching_snapshot_count": mismatching_snapshot_count,
        "execution_snapshot_drift_report_path": report_path,
    }


def _snapshot_target_matched(current: Any, target: Any) -> bool:
    if isinstance(target, Sequence) and not isinstance(target, (str, bytes, bytearray)):
        return current in target
    return current == target


def compare_signal_snapshots(
    previous_snapshot: Mapping[str, Any] | None,
    current_snapshot: Mapping[str, Any] | None,
    target_snapshot: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    previous = dict(previous_snapshot) if isinstance(previous_snapshot, Mapping) else {}
    current = dict(current_snapshot) if isinstance(current_snapshot, Mapping) else {}
    target = dict(target_snapshot) if isinstance(target_snapshot, Mapping) else {}
    keys = list(dict.fromkeys([*previous.keys(), *current.keys(), *target.keys()]))
    diffs: dict[str, dict[str, Any]] = {}
    for key in keys:
        previous_value = previous.get(key)
        current_value = current.get(key)
        target_value = target.get(key)
        previous_target_matched = _snapshot_target_matched(previous_value, target_value)
        current_target_matched = _snapshot_target_matched(current_value, target_value)
        if key not in previous:
            trend = "new"
        elif current_value == previous_value:
            trend = "unchanged"
        elif current_target_matched and not previous_target_matched:
            trend = "improved"
        elif previous_target_matched and not current_target_matched:
            trend = "regressed"
        else:
            trend = "changed"
        diffs[key] = {
            "previous": previous_value,
            "current": current_value,
            "target": target_value,
            "trend": trend,
            "target_matched": current_target_matched,
        }
    return diffs


def _flatten_observed_sources(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        flattened: list[str] = []
        for nested in value:
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    return []


def source_confidence_for_observed_sources(observed_sources: Sequence[str] | None) -> str | None:
    values = [str(source) for source in (observed_sources or []) if isinstance(source, str)]
    if not values:
        return None
    best_rank = min(_SOURCE_QUALITY_RANKS.get(source, 3) for source in values)
    if best_rank == 0:
        return "high"
    if best_rank == 1:
        return "medium"
    return "low"


def signal_observed_sources_by_reason(
    evaluator_summary: Mapping[str, Any] | None,
    *,
    source: str,
) -> dict[str, dict[str, Any]]:
    actions = evaluator_summary.get("actions") if isinstance(evaluator_summary, Mapping) else None
    if not isinstance(actions, Sequence):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in actions:
        if not isinstance(item, Mapping) or item.get("source") != source or not item.get("reason"):
            continue
        reason = str(item.get("reason"))
        reason_map = mapped.setdefault(reason, {})
        signal_evaluations = item.get("signal_evaluations")
        if not isinstance(signal_evaluations, Sequence):
            continue
        for signal in signal_evaluations:
            if not isinstance(signal, Mapping) or not isinstance(signal.get("signal"), str):
                continue
            reason_map[str(signal.get("signal"))] = signal.get("observed_source")
    return mapped


def signal_source_confidence(
    signal_observed_sources: Mapping[str, Any] | None,
    signals: Sequence[str] | None,
) -> str | None:
    if not isinstance(signal_observed_sources, Mapping) or not signals:
        return None
    flattened: list[str] = []
    for signal in signals:
        if not isinstance(signal, str):
            continue
        flattened.extend(_flatten_observed_sources(signal_observed_sources.get(signal)))
    return source_confidence_for_observed_sources(flattened)


def recommend_remediation_actions(
    diffs: Mapping[str, Mapping[str, Any]] | None,
    *,
    preflight_commands: Sequence[str] | None = None,
    execute_commands: Sequence[str] | None = None,
    postcheck_commands: Sequence[str] | None = None,
    source_confidence: str | None = None,
    source_policy: str | None = None,
    execute_signal_confidence: str | None = None,
    postcheck_signal_confidence: str | None = None,
) -> dict[str, Any]:
    items = dict(diffs) if isinstance(diffs, Mapping) else {}
    preflight = list(preflight_commands or [])
    execute = list(execute_commands or [])
    postcheck = list(postcheck_commands or [])
    confidence = str(source_confidence or "").strip() or None
    policy = str(source_policy or "").strip() or None
    execute_confidence = str(execute_signal_confidence or "").strip() or None
    postcheck_confidence = str(postcheck_signal_confidence or "").strip() or None
    if not items:
        response = {"status": "no_signals", "commands": [], "why": "no remediation signals available"}
        if confidence:
            response["source_confidence"] = confidence
        if policy:
            response["source_policy"] = policy
        return response
    values = [item for item in items.values() if isinstance(item, Mapping)]
    response: dict[str, Any]
    if values and all(bool(item.get("target_matched")) for item in values):
        response = {
            "status": "matched",
            "commands": postcheck,
            "why": "all current signals match target values",
        }
    elif any(item.get("trend") == "regressed" for item in values):
        response = {
            "status": "regressed",
            "commands": preflight or execute,
            "why": "one or more signals regressed away from target",
        }
    elif any(item.get("trend") in {"improved", "changed", "new"} for item in values):
        commands = execute or postcheck
        why = "signals changed but target is not fully matched yet"
        if execute_confidence == "low" or postcheck_confidence == "low":
            commands = preflight or commands
            why = "signals changed but low-confidence verification sources require revalidation before execute"
        elif confidence == "low":
            commands = preflight or commands
            why = "signals changed but low-confidence sources require revalidation before execute"
        response = {
            "status": "improving",
            "commands": commands,
            "why": why,
        }
    else:
        response = {
            "status": "stalled",
            "commands": execute or preflight,
            "why": "signals did not move toward target",
        }
    if confidence:
        response["source_confidence"] = confidence
    if policy:
        response["source_policy"] = policy
    if execute_confidence:
        response["execute_signal_confidence"] = execute_confidence
    if postcheck_confidence:
        response["postcheck_signal_confidence"] = postcheck_confidence
    return response
