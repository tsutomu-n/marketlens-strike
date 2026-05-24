from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import read_jsonl, write_json


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


def build_execution_state_comparison_history_report(
    *,
    operation_chain_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
    limit: int = 12,
) -> str:
    operations = list(read_jsonl(operation_chain_path)) if operation_chain_path and operation_chain_path.exists() else []
    relevant_ops = {
        "paper_operations_cycle",
        "operations_snapshot",
        "operations_audit_snapshot",
        "audit_bundle_snapshot",
        "daemon_dry_run",
    }
    entries: list[dict[str, object]] = []
    for item in operations:
        operation = str(item.get("operation"))
        if operation not in relevant_ops:
            continue
        notes = item.get("notes", [])
        if not isinstance(notes, list):
            continue
        diagnostics_status = _note_value(notes, "execution_diagnostics_status=")
        gap_history_diagnostics_status = _note_value(notes, "execution_gap_history_latest_diagnostics_status=")
        if diagnostics_status is None and gap_history_diagnostics_status is None:
            continue
        status_match = (
            diagnostics_status == gap_history_diagnostics_status
            if diagnostics_status is not None and gap_history_diagnostics_status is not None
            else None
        )
        entries.append(
            {
                "created_at": item.get("created_at"),
                "operation": operation,
                "status": item.get("status"),
                "execution_diagnostics_status": diagnostics_status,
                "execution_gap_history_latest_diagnostics_status": gap_history_diagnostics_status,
                "status_match": status_match,
            }
        )

    latest = entries[-1] if entries else {}
    diagnostics_counts = _count_values(
        [
            str(item.get("execution_diagnostics_status"))
            if item.get("execution_diagnostics_status") is not None
            else None
            for item in entries
        ]
    )
    gap_history_diagnostics_counts = _count_values(
        [
            str(item.get("execution_gap_history_latest_diagnostics_status"))
            if item.get("execution_gap_history_latest_diagnostics_status") is not None
            else None
            for item in entries
        ]
    )
    pair_counts = _count_values(
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
    matching_count = sum(1 for item in entries if item.get("status_match") is True)
    mismatching_count = sum(1 for item in entries if item.get("status_match") is False)

    summary = {
        "entry_count": len(entries),
        "latest_operation": latest.get("operation"),
        "latest_status": latest.get("status"),
        "latest_created_at": latest.get("created_at"),
        "latest_execution_diagnostics_status": latest.get("execution_diagnostics_status"),
        "latest_execution_gap_history_diagnostics_status": latest.get(
            "execution_gap_history_latest_diagnostics_status"
        ),
        "latest_status_match": latest.get("status_match"),
        "execution_state_comparison_entry_count": len(entries),
        "execution_state_comparison_latest_status": latest.get("status"),
        "execution_state_comparison_latest_diagnostics_status": latest.get(
            "execution_diagnostics_status"
        ),
        "execution_state_comparison_latest_status_match": latest.get("status_match"),
        "execution_state_comparison_mismatching_count": mismatching_count,
        "execution_state_comparison_report_path": str(out_path) if out_path is not None else None,
        "matching_count": matching_count,
        "mismatching_count": mismatching_count,
        "diagnostics_counts": diagnostics_counts,
        "gap_history_diagnostics_counts": gap_history_diagnostics_counts,
        "pair_counts": pair_counts,
    }

    lines = [
        "# Execution State Comparison History",
        "",
        "## Summary",
        "",
        f"- entry_count: {summary['entry_count']}",
        f"- latest_operation: {summary['latest_operation']}",
        f"- latest_status: {summary['latest_status']}",
        f"- latest_created_at: {summary['latest_created_at']}",
        f"- latest_execution_diagnostics_status: {summary['latest_execution_diagnostics_status']}",
        (
            "- latest_execution_gap_history_diagnostics_status: "
            f"{summary['latest_execution_gap_history_diagnostics_status']}"
        ),
        f"- latest_status_match: {summary['latest_status_match']}",
        f"- matching_count: {summary['matching_count']}",
        f"- mismatching_count: {summary['mismatching_count']}",
        "",
        "## Diagnostics Counts",
        "",
    ]
    if diagnostics_counts:
        for key in sorted(diagnostics_counts):
            lines.append(f"- {key}: {diagnostics_counts[key]}")
    else:
        lines.append("- no execution diagnostics status notes were available")
    lines.extend(["", "## Gap History Diagnostics Counts", ""])
    if gap_history_diagnostics_counts:
        for key in sorted(gap_history_diagnostics_counts):
            lines.append(f"- {key}: {gap_history_diagnostics_counts[key]}")
    else:
        lines.append("- no gap history diagnostics status notes were available")
    lines.extend(["", "## Pair Counts", ""])
    if pair_counts:
        for key in sorted(pair_counts):
            lines.append(f"- {key}: {pair_counts[key]}")
    else:
        lines.append("- no comparison pairs were available")
    lines.extend(["", "## Recent Changes", ""])
    if entries:
        for item in entries[-limit:]:
            lines.append(
                "- "
                f"{item.get('created_at')} | op={item.get('operation')} | status={item.get('status')} | "
                f"diagnostics={item.get('execution_diagnostics_status')} | "
                f"gap_history={item.get('execution_gap_history_latest_diagnostics_status')} | "
                f"match={item.get('status_match')}"
            )
    else:
        lines.append("- no execution state comparison entries available")
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
