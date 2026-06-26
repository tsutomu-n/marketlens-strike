from __future__ import annotations

from typing import Any, Mapping, Sequence


def latest_execution_section_lines(
    title: str,
    execution_summary: Mapping[str, Any] | None,
    execution_comparison_summary: Mapping[str, Any] | None,
) -> list[str]:
    from sis.reports.execution_lineage_normalizers import (
        execution_comparison_flat_fields,
        execution_snapshot_flat_fields,
        normalize_execution_comparison_summary,
        normalize_execution_snapshot_summary,
    )

    normalized_execution_summary = normalize_execution_snapshot_summary(execution_summary)
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
