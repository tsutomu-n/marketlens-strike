from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.reports.summary_normalizers import (
    execution_gap_history_flat_fields,
    first_remapped_latest_execution_lineage_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_state_comparison_summary,
)
from sis.storage.jsonl_store import write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_drift_overview_report": str(out_path),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(reports_dir / "execution_state_comparison_history.md"),
        "execution_snapshot_drift_report": str(reports_dir / "execution_snapshot_drift_history.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_drift_overview_report": str(out_path),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(reports_dir / "execution_state_comparison_history.md"),
        "execution_snapshot_drift_report": str(reports_dir / "execution_snapshot_drift_history.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
    }


def build_execution_drift_overview_report(
    *,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    gap_history = safe_read_json_dict(execution_gap_history_summary_path)
    state_comparison = safe_read_json_dict(execution_state_comparison_history_summary_path)
    snapshot_drift = safe_read_json_dict(execution_snapshot_drift_history_summary_path)
    gap_history_summary = normalize_execution_gap_history_summary(gap_history)
    state_comparison_summary = normalize_execution_state_comparison_summary(state_comparison)
    snapshot_drift_summary = normalize_execution_snapshot_drift_summary(snapshot_drift)
    gap_history_fields = execution_gap_history_flat_fields(gap_history_summary)
    state_comparison_fields = execution_state_comparison_flat_fields(state_comparison_summary)
    snapshot_drift_fields = execution_snapshot_drift_flat_fields(snapshot_drift_summary)
    latest_execution_lineage = first_remapped_latest_execution_lineage_fields(
        (snapshot_drift_summary, "latest"),
        (state_comparison_summary, "latest"),
        (gap_history_summary, "latest"),
    )

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
        **latest_execution_lineage,
        "execution_drift_overview_report_path": str(out_path) if out_path is not None else None,
        "execution_gap_history_summary": gap_history_summary,
        "execution_state_comparison_summary": state_comparison_summary,
        "execution_snapshot_drift_summary": snapshot_drift_summary,
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
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }

    lines = ["# Execution Drift Overview", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(
        [
            "## Summary",
            "",
            f"- overall_status: {summary['overall_status']}",
            f"- latest_execution_overall_status: {summary['latest_execution_overall_status']}",
            f"- latest_execution_venue_count: {summary['latest_execution_venue_count']}",
            (
                "- latest_execution_comparison_all_registries_present: "
                f"{summary['latest_execution_comparison_all_registries_present']}"
            ),
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
    )
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
