from __future__ import annotations

from typing import Any, Mapping


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
        "timeline_latest_execution_gap_history_status": payload.get(
            "latest_execution_gap_history_status"
        ),
        "timeline_latest_execution_gap_history_diagnostics_status": payload.get(
            "latest_execution_gap_history_diagnostics_status"
        ),
        "timeline_latest_readiness_execution_ready": payload.get(
            "latest_readiness_execution_ready"
        ),
    }


def audit_bundle_history_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    return {
        "bundle_history_snapshot_count": payload.get("snapshot_count"),
        "bundle_history_ok_count": payload.get("ok_count"),
        "bundle_history_latest_execution_gap_history_status": payload.get(
            "latest_execution_gap_history_status"
        ),
        "bundle_history_latest_execution_gap_history_diagnostics_status": payload.get(
            "latest_execution_gap_history_diagnostics_status"
        ),
        "bundle_history_latest_readiness_execution_ready": payload.get(
            "latest_readiness_execution_ready"
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
    report_path = payload.get("report_path") or payload.get("execution_comparison_report_path")
    return {
        **payload,
        "all_registries_present": all_registries_present,
        "report_path": report_path,
        "execution_comparison_all_registries_present": all_registries_present,
        "execution_comparison_report_path": report_path,
    }


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
