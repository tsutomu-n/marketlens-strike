from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    latest_execution_lineage_from_notes,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_state_comparison_summary,
    normalize_readiness_summary,
)
from sis.storage.jsonl_store import read_jsonl, write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_drift_report": str(out_path),
        "execution_state_comparison_report": str(
            reports_dir / "execution_state_comparison_history.md"
        ),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_drift_report": str(out_path),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(
            reports_dir / "execution_state_comparison_history.md"
        ),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _note_value(notes: list[object], prefix: str) -> str | None:
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return None


def _count_values(values: list[str | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def build_execution_snapshot_drift_history_report(
    *,
    operation_chain_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
    limit: int = 12,
) -> str:
    operations = (
        list(read_jsonl(operation_chain_path))
        if operation_chain_path and operation_chain_path.exists()
        else []
    )
    relevant_ops = {"operations_snapshot", "operations_audit_snapshot", "audit_bundle_snapshot"}
    entries: list[dict[str, object]] = []
    for item in operations:
        operation = str(item.get("operation"))
        if operation not in relevant_ops:
            continue
        notes = item.get("notes", [])
        if not isinstance(notes, list):
            continue
        diagnostics_status = _note_value(notes, "execution_diagnostics_status=")
        latest_execution_lineage = latest_execution_lineage_from_notes(notes, prefix="latest")
        gap_history_diagnostics_status = _note_value(
            notes, "execution_gap_history_latest_diagnostics_status="
        )
        state_comparison_status_match = _note_value(
            notes, "execution_state_comparison_latest_status_match="
        )
        state_comparison_mismatching_count = _note_value(
            notes, "execution_state_comparison_mismatching_count="
        )
        readiness_next_phase = _note_value(notes, "readiness_next_phase=")
        readiness_execution_ready = _note_value(notes, "readiness_execution_ready=")
        if (
            diagnostics_status is None
            and gap_history_diagnostics_status is None
            and state_comparison_status_match is None
            and state_comparison_mismatching_count is None
        ):
            continue
        entries.append(
            {
                "created_at": item.get("created_at"),
                "operation": operation,
                "status": item.get("status"),
                "execution_overall_status": latest_execution_lineage.get(
                    "latest_execution_overall_status"
                ),
                "execution_venue_count": latest_execution_lineage.get(
                    "latest_execution_venue_count"
                ),
                "execution_comparison_all_registries_present": latest_execution_lineage.get(
                    "latest_execution_comparison_all_registries_present"
                ),
                "execution_diagnostics_status": diagnostics_status,
                "execution_gap_history_latest_diagnostics_status": gap_history_diagnostics_status,
                "execution_state_comparison_latest_status_match": state_comparison_status_match,
                "execution_state_comparison_mismatching_count": state_comparison_mismatching_count,
                "readiness_next_phase": readiness_next_phase,
                "readiness_execution_ready": readiness_execution_ready,
            }
        )

    latest = entries[-1] if entries else {}
    diagnostics_pair_counts = _count_values(
        [
            (
                f"{item.get('execution_diagnostics_status')} -> "
                f"{item.get('execution_gap_history_latest_diagnostics_status')}"
            )
            if item.get("execution_diagnostics_status") is not None
            or item.get("execution_gap_history_latest_diagnostics_status") is not None
            else None
            for item in entries
        ]
    )
    state_comparison_status_match_counts = _count_values(
        [
            str(item.get("execution_state_comparison_latest_status_match"))
            if item.get("execution_state_comparison_latest_status_match") is not None
            else None
            for item in entries
        ]
    )
    state_comparison_mismatching_count_values = _count_values(
        [
            str(item.get("execution_state_comparison_mismatching_count"))
            if item.get("execution_state_comparison_mismatching_count") is not None
            else None
            for item in entries
        ]
    )
    readiness_next_phase_counts = _count_values(
        [
            str(item.get("readiness_next_phase"))
            if item.get("readiness_next_phase") is not None
            else None
            for item in entries
        ]
    )
    readiness_execution_ready_counts = _count_values(
        [
            str(item.get("readiness_execution_ready"))
            if item.get("readiness_execution_ready") is not None
            else None
            for item in entries
        ]
    )
    matching_snapshot_count = sum(
        1
        for item in entries
        if str(item.get("execution_state_comparison_latest_status_match")) == "True"
    )
    mismatching_snapshot_count = sum(
        1
        for item in entries
        if str(item.get("execution_state_comparison_latest_status_match")) == "False"
    )
    latest_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        {"overall_status": latest.get("execution_diagnostics_status")}
    )
    latest_execution_lineage = latest_execution_lineage_from_notes(
        [
            f"execution_overall_status={latest.get('execution_overall_status')}",
            f"execution_venue_count={latest.get('execution_venue_count')}",
            "execution_comparison_all_registries_present="
            f"{latest.get('execution_comparison_all_registries_present')}",
        ],
        prefix="latest",
    )
    latest_execution_gap_history_summary = normalize_execution_gap_history_summary(
        {
            "latest_status": latest.get("status"),
            "latest_execution_diagnostics_status": latest.get(
                "execution_gap_history_latest_diagnostics_status"
            ),
        }
    )
    latest_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        {
            "latest_status": latest.get("status"),
            "latest_status_match": latest.get("execution_state_comparison_latest_status_match"),
            "mismatching_count": latest.get("execution_state_comparison_mismatching_count"),
            "latest_execution_diagnostics_status": latest.get("execution_diagnostics_status"),
        }
    )
    latest_readiness_summary = normalize_readiness_summary(
        {
            "readiness_next_phase_candidate": latest.get("readiness_next_phase"),
            "readiness_execution_ready": latest.get("readiness_execution_ready"),
        }
    )

    summary = {
        "entry_count": len(entries),
        "latest_operation": latest.get("operation"),
        "latest_status": latest.get("status"),
        "latest_created_at": latest.get("created_at"),
        "latest_execution_diagnostics_status": latest.get("execution_diagnostics_status"),
        "latest_execution_gap_history_diagnostics_status": latest.get(
            "execution_gap_history_latest_diagnostics_status"
        ),
        **latest_execution_lineage,
        "latest_execution_state_comparison_status_match": latest.get(
            "execution_state_comparison_latest_status_match"
        ),
        "latest_execution_state_comparison_mismatching_count": latest.get(
            "execution_state_comparison_mismatching_count"
        ),
        "execution_snapshot_drift_entry_count": len(entries),
        "execution_snapshot_drift_latest_status": latest.get("status"),
        "execution_snapshot_drift_latest_diagnostics_status": latest.get(
            "execution_diagnostics_status"
        ),
        "execution_snapshot_drift_latest_status_match": latest.get(
            "execution_state_comparison_latest_status_match"
        ),
        "execution_snapshot_drift_latest_mismatching_count": latest.get(
            "execution_state_comparison_mismatching_count"
        ),
        "execution_snapshot_drift_mismatching_snapshot_count": mismatching_snapshot_count,
        "execution_snapshot_drift_report_path": str(out_path) if out_path is not None else None,
        "latest_readiness_next_phase": latest.get("readiness_next_phase"),
        "latest_readiness_execution_ready": latest.get("readiness_execution_ready"),
        "matching_snapshot_count": matching_snapshot_count,
        "mismatching_snapshot_count": mismatching_snapshot_count,
        "diagnostics_pair_counts": diagnostics_pair_counts,
        "state_comparison_status_match_counts": state_comparison_status_match_counts,
        "state_comparison_mismatching_count_values": state_comparison_mismatching_count_values,
        "readiness_next_phase_counts": readiness_next_phase_counts,
        "readiness_execution_ready_counts": readiness_execution_ready_counts,
        "latest_execution_diagnostics_summary": latest_execution_diagnostics_summary,
        "latest_execution_gap_history_summary": latest_execution_gap_history_summary,
        "latest_execution_state_comparison_summary": latest_execution_state_comparison_summary,
        "latest_readiness_summary": latest_readiness_summary,
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path)
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports

    lines = ["# Execution Snapshot Drift History", ""]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(
        [
            "## Summary",
            "",
            f"- entry_count: {summary['entry_count']}",
            f"- latest_operation: {summary['latest_operation']}",
            f"- latest_status: {summary['latest_status']}",
            f"- latest_created_at: {summary['latest_created_at']}",
            f"- latest_execution_overall_status: {summary['latest_execution_overall_status']}",
            f"- latest_execution_venue_count: {summary['latest_execution_venue_count']}",
            (
                "- latest_execution_comparison_all_registries_present: "
                f"{summary['latest_execution_comparison_all_registries_present']}"
            ),
            f"- latest_execution_diagnostics_status: {summary['latest_execution_diagnostics_status']}",
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
            f"- matching_snapshot_count: {summary['matching_snapshot_count']}",
            f"- mismatching_snapshot_count: {summary['mismatching_snapshot_count']}",
            "",
            "## Diagnostics Pair Counts",
            "",
        ]
    )
    if diagnostics_pair_counts:
        for key in sorted(diagnostics_pair_counts):
            lines.append(f"- {key}: {diagnostics_pair_counts[key]}")
    else:
        lines.append("- no diagnostics drift pairs were available")
    lines.extend(["", "## State Comparison Status Match Counts", ""])
    if state_comparison_status_match_counts:
        for key in sorted(state_comparison_status_match_counts):
            lines.append(f"- {key}: {state_comparison_status_match_counts[key]}")
    else:
        lines.append("- no state comparison match notes were available")
    lines.extend(["", "## State Comparison Mismatching Count Values", ""])
    if state_comparison_mismatching_count_values:
        for key in sorted(state_comparison_mismatching_count_values):
            lines.append(f"- {key}: {state_comparison_mismatching_count_values[key]}")
    else:
        lines.append("- no state comparison mismatch notes were available")
    lines.extend(["", "## Readiness Next Phase Counts", ""])
    if readiness_next_phase_counts:
        for key in sorted(readiness_next_phase_counts):
            lines.append(f"- {key}: {readiness_next_phase_counts[key]}")
    else:
        lines.append("- no readiness next phase notes were available")
    lines.extend(["", "## Readiness Execution Ready Counts", ""])
    if readiness_execution_ready_counts:
        for key in sorted(readiness_execution_ready_counts):
            lines.append(f"- {key}: {readiness_execution_ready_counts[key]}")
    else:
        lines.append("- no readiness execution-ready notes were available")
    lines.extend(["", "## Recent Changes", ""])
    if entries:
        for item in entries[-limit:]:
            lines.append(
                "- "
                f"{item.get('created_at')} | op={item.get('operation')} | status={item.get('status')} | "
                f"execution={item.get('execution_overall_status')} | venues={item.get('execution_venue_count')} | "
                f"registries={item.get('execution_comparison_all_registries_present')} | "
                f"diagnostics={item.get('execution_diagnostics_status')} | "
                f"gap_history={item.get('execution_gap_history_latest_diagnostics_status')} | "
                f"state_match={item.get('execution_state_comparison_latest_status_match')} | "
                f"mismatch_count={item.get('execution_state_comparison_mismatching_count')} | "
                f"next_phase={item.get('readiness_next_phase')} | "
                f"execution_ready={item.get('readiness_execution_ready')}"
            )
    else:
        lines.append("- no execution snapshot drift entries available")
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
