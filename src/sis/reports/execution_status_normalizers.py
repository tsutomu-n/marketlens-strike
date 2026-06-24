from __future__ import annotations

from typing import Any, Mapping


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
    reason_codes = payload.get("execution_drift_overview_reason_codes")
    if not isinstance(reason_codes, list):
        reason_codes = []
    lineage = payload.get("execution_drift_overview_lineage")
    return {
        **payload,
        "overall_status": overall_status,
        "reason_codes": reason_codes,
        "lineage": lineage,
        "diagnostics_alignment_match": diagnostics_alignment_match,
        "state_comparison_mismatching_count": state_comparison_mismatching_count,
        "snapshot_drift_mismatching_snapshot_count": snapshot_drift_mismatching_snapshot_count,
        "execution_drift_overview_status": overall_status,
        "execution_drift_overview_reason_codes": reason_codes,
        "execution_drift_overview_lineage": lineage,
        "execution_drift_overview_diagnostics_alignment_match": diagnostics_alignment_match,
        "execution_drift_overview_state_comparison_mismatching_count": (
            state_comparison_mismatching_count
        ),
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            snapshot_drift_mismatching_snapshot_count
        ),
    }


def execution_drift_overview_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_drift_overview_summary(summary)
    return {
        "execution_drift_overview_status": payload.get("execution_drift_overview_status"),
        "execution_drift_overview_reason_codes": payload.get(
            "execution_drift_overview_reason_codes"
        ),
        "execution_drift_overview_lineage": payload.get("execution_drift_overview_lineage"),
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


def execution_diagnostics_flat_fields(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = normalize_execution_diagnostics_summary(summary)
    return {
        "execution_diagnostics_status": payload.get("overall_status"),
        "execution_diagnostics_reason": payload.get("diagnostics_reason"),
        "execution_diagnostics_root_source": payload.get("diagnostics_root_source"),
        "execution_balance_gap_detected": payload.get("balance_gap_detected"),
        "execution_positions_snapshot_gap_detected": payload.get("positions_snapshot_gap_detected"),
        "execution_fills_gap_detected": payload.get("fills_gap_detected"),
        "execution_diagnostics_report_path": payload.get("report_path"),
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
    positions_snapshot_gap_detected = (
        payload.get("positions_snapshot_gap_detected")
        if payload.get("positions_snapshot_gap_detected") is not None
        else payload.get("execution_positions_snapshot_gap_detected")
    )
    fills_gap_detected = (
        payload.get("fills_gap_detected")
        if payload.get("fills_gap_detected") is not None
        else payload.get("execution_fills_gap_detected")
    )
    report_path = payload.get("report_path") or payload.get("execution_diagnostics_report_path")
    diagnostics_reason = payload.get("diagnostics_reason") or payload.get(
        "execution_diagnostics_reason"
    )
    diagnostics_root_source = payload.get("diagnostics_root_source") or payload.get(
        "execution_diagnostics_root_source"
    )
    return {
        **payload,
        "overall_status": overall_status,
        "diagnostics_reason": diagnostics_reason,
        "diagnostics_root_source": diagnostics_root_source,
        "balance_gap_detected": balance_gap_detected,
        "positions_snapshot_gap_detected": positions_snapshot_gap_detected,
        "fills_gap_detected": fills_gap_detected,
        "report_path": report_path,
        "execution_diagnostics_status": overall_status,
        "execution_diagnostics_reason": diagnostics_reason,
        "execution_diagnostics_root_source": diagnostics_root_source,
        "execution_balance_gap_detected": balance_gap_detected,
        "execution_positions_snapshot_gap_detected": positions_snapshot_gap_detected,
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


def normalize_execution_gap_history_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    entry_count = (
        payload.get("entry_count")
        if payload.get("entry_count") is not None
        else payload.get("execution_gap_history_entry_count")
    )
    latest_status = payload.get("latest_status") or payload.get(
        "execution_gap_history_latest_status"
    )
    latest_execution_diagnostics_status = payload.get(
        "latest_execution_diagnostics_status"
    ) or payload.get("execution_gap_history_latest_diagnostics_status")
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


def normalize_execution_state_comparison_summary(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    entry_count = (
        payload.get("entry_count")
        if payload.get("entry_count") is not None
        else payload.get("execution_state_comparison_entry_count")
    )
    latest_status = payload.get("latest_status") or payload.get(
        "execution_state_comparison_latest_status"
    )
    latest_execution_diagnostics_status = payload.get(
        "latest_execution_diagnostics_status"
    ) or payload.get("execution_state_comparison_latest_diagnostics_status")
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
    report_path = payload.get("report_path") or payload.get(
        "execution_state_comparison_report_path"
    )
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


def normalize_execution_snapshot_drift_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    if not payload:
        return {}
    entry_count = (
        payload.get("entry_count")
        if payload.get("entry_count") is not None
        else payload.get("execution_snapshot_drift_entry_count")
    )
    latest_status = payload.get("latest_status") or payload.get(
        "execution_snapshot_drift_latest_status"
    )
    latest_execution_diagnostics_status = payload.get(
        "latest_execution_diagnostics_status"
    ) or payload.get("execution_snapshot_drift_latest_diagnostics_status")
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
