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
    next_phase_candidate = payload.get("next_phase_candidate") or payload.get(
        "readiness_next_phase_candidate"
    )
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


def phase_gate_nested_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_phase_gate_summary(summary)
    return {
        "decision": payload.get("decision"),
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
        f"phase_gate_issue_{index}={preview}" for index, preview in enumerate(previews, start=1)
    ]


def readiness_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_readiness_summary(summary)
    return {
        "readiness_next_phase_candidate": payload.get("readiness_next_phase_candidate"),
        "readiness_execution_ready": payload.get("readiness_execution_ready"),
    }
