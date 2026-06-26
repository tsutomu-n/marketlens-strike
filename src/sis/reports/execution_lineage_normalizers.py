from __future__ import annotations

from typing import Any, Mapping, Sequence

from sis.reports.execution_lineage_sections import (
    latest_execution_flat_lines,
    latest_execution_flat_section_lines,
    latest_execution_flat_sections,
    latest_execution_lineage_flat_lines,
    latest_execution_section_lines,
    latest_execution_sections,
)

__all__ = [
    "all_latest_execution_lineage_fields",
    "defaulted_all_latest_execution_lineage_fields",
    "execution_comparison_flat_fields",
    "execution_snapshot_flat_fields",
    "first_remapped_latest_execution_lineage_fields",
    "latest_execution_flat_lines",
    "latest_execution_flat_section_lines",
    "latest_execution_flat_sections",
    "latest_execution_lineage_fields",
    "latest_execution_lineage_fields_from_payload",
    "latest_execution_lineage_fields_from_summary",
    "latest_execution_lineage_flat_lines",
    "latest_execution_lineage_from_notes",
    "latest_execution_lineage_from_values",
    "latest_execution_lineage_payload",
    "latest_execution_lineage_payload_from_summary",
    "latest_execution_payload_and_fields_from_summary",
    "latest_execution_section_lines",
    "latest_execution_sections",
    "merged_latest_execution_lineage_fields",
    "merged_latest_execution_payload_and_fields",
    "merged_remapped_latest_execution_lineage_fields",
    "normalize_execution_comparison_summary",
    "normalize_execution_snapshot_summary",
    "remap_latest_execution_lineage_fields",
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
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison_summary)
    return {
        f"{prefix}_execution_summary": execution_summary,
        f"{prefix}_execution_comparison_summary": execution_comparison_summary,
        f"{prefix}_execution_overall_status": execution_fields.get("execution_overall_status"),
        f"{prefix}_execution_venue_count": execution_fields.get("execution_venue_count"),
        f"{prefix}_execution_snapshot_reason": execution_fields.get("execution_snapshot_reason"),
        f"{prefix}_execution_snapshot_next_action": execution_fields.get(
            "execution_snapshot_next_action"
        ),
        f"{prefix}_execution_comparison_all_registries_present": (
            execution_comparison_fields.get("execution_comparison_all_registries_present")
        ),
    }


def latest_execution_lineage_from_values(
    *,
    prefix: str,
    overall_status: Any,
    venue_count: Any,
    all_registries_present: Any,
    snapshot_reason: Any = None,
    snapshot_next_action: Any = None,
) -> dict[str, Any]:
    return latest_execution_lineage_fields(
        {
            f"{prefix}_execution_summary": {
                "overall_status": overall_status,
                "venue_count": venue_count,
                "execution_snapshot_reason": snapshot_reason,
                "execution_snapshot_next_action": snapshot_next_action,
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

    def _optional_note_value(note_prefix: str) -> str | None:
        value = _note_value(note_prefix)
        return None if value in {None, "", "None"} else value

    return latest_execution_lineage_from_values(
        prefix=prefix,
        overall_status=_note_value("execution_overall_status="),
        venue_count=_note_value("execution_venue_count="),
        all_registries_present=_note_value("execution_comparison_all_registries_present="),
        snapshot_reason=_optional_note_value("execution_snapshot_reason="),
        snapshot_next_action=_optional_note_value("execution_snapshot_next_action="),
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
        "bundle_history_latest_execution_summary": (bundle_history_latest_execution_summary),
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
        timeline_latest_execution_summary=payload.get("timeline_latest_execution_summary"),
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
            bundle_history_latest_execution_summary=(bundle_history_latest_execution_summary),
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
            or payload.get(f"{prefix}_execution_comparison_all_registries_present") is not None
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
        merged.update(remap_latest_execution_lineage_fields(summary, target_prefix=target_prefix))
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
