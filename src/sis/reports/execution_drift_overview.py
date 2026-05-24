from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
)
from sis.storage.jsonl_store import read_json, write_json


def _safe_read_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def build_execution_drift_overview_report(
    *,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    gap_history = _safe_read_json(execution_gap_history_summary_path)
    state_comparison = _safe_read_json(execution_state_comparison_history_summary_path)
    snapshot_drift = _safe_read_json(execution_snapshot_drift_history_summary_path)
    gap_history_fields = execution_gap_history_flat_fields(gap_history)
    state_comparison_fields = execution_state_comparison_flat_fields(state_comparison)
    snapshot_drift_fields = execution_snapshot_drift_flat_fields(snapshot_drift)

    diagnostics_alignment_match = (
        state_comparison_fields.get("execution_state_comparison_latest_diagnostics_status")
        == gap_history_fields.get("execution_gap_history_latest_diagnostics_status")
        if state_comparison_fields.get("execution_state_comparison_latest_diagnostics_status") is not None
        and gap_history_fields.get("execution_gap_history_latest_diagnostics_status") is not None
        else None
    )
    state_comparison_match = state_comparison_fields.get("execution_state_comparison_latest_status_match")
    snapshot_drift_match = snapshot_drift_fields.get("execution_snapshot_drift_latest_status_match")
    overall_status = (
        "ok"
        if int(gap_history_fields.get("execution_gap_history_entry_count") or 0) > 0
        and state_comparison_match is True
        and int(state_comparison_fields.get("execution_state_comparison_mismatching_count") or 0) == 0
        and snapshot_drift_match is True
        and int(snapshot_drift_fields.get("execution_snapshot_drift_mismatching_snapshot_count") or 0) == 0
        and diagnostics_alignment_match is True
        else "degraded"
    )

    summary = {
        "overall_status": overall_status,
        "gap_history_entry_count": gap_history_fields.get("execution_gap_history_entry_count"),
        "latest_gap_history_status": gap_history_fields.get("execution_gap_history_latest_status"),
        "latest_gap_history_diagnostics_status": gap_history_fields.get(
            "execution_gap_history_latest_diagnostics_status"
        ),
        "state_comparison_latest_status_match": state_comparison_match,
        "state_comparison_mismatching_count": state_comparison_fields.get(
            "execution_state_comparison_mismatching_count"
        ),
        "snapshot_drift_latest_status_match": snapshot_drift_match,
        "snapshot_drift_mismatching_snapshot_count": snapshot_drift_fields.get(
            "execution_snapshot_drift_mismatching_snapshot_count"
        ),
        "diagnostics_alignment_match": diagnostics_alignment_match,
        "execution_drift_overview_status": overall_status,
        "execution_drift_overview_diagnostics_alignment_match": diagnostics_alignment_match,
        "execution_drift_overview_state_comparison_mismatching_count": state_comparison_fields.get(
            "execution_state_comparison_mismatching_count"
        ),
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": snapshot_drift_fields.get(
            "execution_snapshot_drift_mismatching_snapshot_count"
        ),
        "execution_drift_overview_report_path": str(out_path) if out_path is not None else None,
        "artifacts": {
            "execution_gap_history_summary": (
                str(execution_gap_history_summary_path) if execution_gap_history_summary_path else None
            ),
            "execution_state_comparison_history_summary": (
                str(execution_state_comparison_history_summary_path)
                if execution_state_comparison_history_summary_path
                else None
            ),
            "execution_snapshot_drift_history_summary": (
                str(execution_snapshot_drift_history_summary_path)
                if execution_snapshot_drift_history_summary_path
                else None
            ),
        },
        "recommended_read_order": [
            "data/ops/execution_drift_overview_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
        ],
    }

    lines = [
        "# Execution Drift Overview",
        "",
        "## Summary",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- gap_history_entry_count: {summary['gap_history_entry_count']}",
        f"- latest_gap_history_status: {summary['latest_gap_history_status']}",
        f"- latest_gap_history_diagnostics_status: {summary['latest_gap_history_diagnostics_status']}",
        f"- state_comparison_latest_status_match: {summary['state_comparison_latest_status_match']}",
        f"- state_comparison_mismatching_count: {summary['state_comparison_mismatching_count']}",
        f"- snapshot_drift_latest_status_match: {summary['snapshot_drift_latest_status_match']}",
        (
            "- snapshot_drift_mismatching_snapshot_count: "
            f"{summary['snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- diagnostics_alignment_match: {summary['diagnostics_alignment_match']}",
        "",
        "## Artifact Paths",
        "",
    ]
    for key, value in summary["artifacts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
