from __future__ import annotations

from typing import Any, Mapping

__all__ = [
    "execution_comparison_flat_fields",
    "execution_snapshot_flat_fields",
    "normalize_execution_comparison_summary",
    "normalize_execution_snapshot_summary",
]


def _normalize_bool_like(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return value


def execution_snapshot_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_snapshot_summary(summary)
    return {
        "execution_overall_status": payload.get("overall_status"),
        "execution_venue_count": payload.get("venue_count"),
        "execution_snapshot_reason": payload.get("execution_snapshot_reason"),
        "execution_snapshot_reason_codes": payload.get("execution_snapshot_reason_codes"),
        "execution_snapshot_root_source": payload.get("execution_snapshot_root_source"),
        "execution_snapshot_next_action": payload.get("execution_snapshot_next_action"),
        "execution_report_path": payload.get("report_path"),
    }


def execution_comparison_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_comparison_summary(summary)
    return {
        "execution_comparison_all_registries_present": payload.get("all_registries_present"),
        "execution_comparison_reason": payload.get("execution_comparison_reason"),
        "execution_comparison_root_source": payload.get("execution_comparison_root_source"),
        "execution_comparison_report_path": payload.get("report_path"),
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
    reason = payload.get("execution_snapshot_reason") or payload.get("snapshot_reason")
    reason_codes = payload.get("execution_snapshot_reason_codes")
    if not isinstance(reason_codes, list):
        reason_codes = [reason] if isinstance(reason, str) else []
    root_source = payload.get("execution_snapshot_root_source")
    next_action = payload.get("execution_snapshot_next_action")
    return {
        **payload,
        "overall_status": overall_status,
        "venue_count": venue_count,
        "report_path": report_path,
        "snapshot_reason": reason,
        "execution_snapshot_reason": reason,
        "execution_snapshot_reason_codes": reason_codes,
        "execution_snapshot_root_source": root_source,
        "execution_snapshot_next_action": next_action,
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
    reason = payload.get("execution_comparison_reason")
    root_source = payload.get("execution_comparison_root_source")
    return {
        **payload,
        "all_registries_present": all_registries_present,
        "report_path": report_path,
        "execution_comparison_reason": reason,
        "execution_comparison_root_source": root_source,
        "execution_comparison_all_registries_present": all_registries_present,
        "execution_comparison_report_path": report_path,
    }
