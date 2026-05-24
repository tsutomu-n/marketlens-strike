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


def build_execution_gap_history_report(
    *,
    operation_chain_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
    limit: int = 10,
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
        readiness_next_phase = _note_value(notes, "readiness_next_phase=")
        readiness_execution_ready = _note_value(notes, "readiness_execution_ready=")
        if diagnostics_status is None and readiness_next_phase is None and readiness_execution_ready is None:
            continue
        entries.append(
            {
                "created_at": item.get("created_at"),
                "operation": operation,
                "status": item.get("status"),
                "diagnostics_status": diagnostics_status,
                "readiness_next_phase": readiness_next_phase,
                "readiness_execution_ready": readiness_execution_ready,
            }
        )

    latest = entries[-1] if entries else {}
    diagnostics_status_counts = _count_values(
        [str(item.get("diagnostics_status")) if item.get("diagnostics_status") is not None else None for item in entries]
    )
    readiness_next_phase_counts = _count_values(
        [str(item.get("readiness_next_phase")) if item.get("readiness_next_phase") is not None else None for item in entries]
    )
    readiness_execution_ready_counts = _count_values(
        [
            str(item.get("readiness_execution_ready")) if item.get("readiness_execution_ready") is not None else None
            for item in entries
        ]
    )

    summary = {
        "entry_count": len(entries),
        "latest_operation": latest.get("operation"),
        "latest_status": latest.get("status"),
        "latest_created_at": latest.get("created_at"),
        "latest_execution_diagnostics_status": latest.get("diagnostics_status"),
        "execution_gap_history_entry_count": len(entries),
        "execution_gap_history_latest_status": latest.get("status"),
        "execution_gap_history_latest_diagnostics_status": latest.get("diagnostics_status"),
        "execution_gap_history_report_path": str(out_path) if out_path is not None else None,
        "latest_readiness_next_phase": latest.get("readiness_next_phase"),
        "latest_readiness_execution_ready": latest.get("readiness_execution_ready"),
        "diagnostics_status_counts": diagnostics_status_counts,
        "readiness_next_phase_counts": readiness_next_phase_counts,
        "readiness_execution_ready_counts": readiness_execution_ready_counts,
    }

    lines = [
        "# Execution Gap History Report",
        "",
        "## Summary",
        "",
        f"- entry_count: {summary['entry_count']}",
        f"- latest_operation: {summary['latest_operation']}",
        f"- latest_status: {summary['latest_status']}",
        f"- latest_created_at: {summary['latest_created_at']}",
        f"- latest_execution_diagnostics_status: {summary['latest_execution_diagnostics_status']}",
        f"- latest_readiness_next_phase: {summary['latest_readiness_next_phase']}",
        f"- latest_readiness_execution_ready: {summary['latest_readiness_execution_ready']}",
        "",
        "## Diagnostics Status Counts",
        "",
    ]
    if diagnostics_status_counts:
        for key in sorted(diagnostics_status_counts):
            lines.append(f"- {key}: {diagnostics_status_counts[key]}")
    else:
        lines.append("- no execution diagnostics history was available")
    lines.extend(["", "## Readiness Next Phase Counts", ""])
    if readiness_next_phase_counts:
        for key in sorted(readiness_next_phase_counts):
            lines.append(f"- {key}: {readiness_next_phase_counts[key]}")
    else:
        lines.append("- no readiness next phase history was available")
    lines.extend(["", "## Readiness Execution Ready Counts", ""])
    if readiness_execution_ready_counts:
        for key in sorted(readiness_execution_ready_counts):
            lines.append(f"- {key}: {readiness_execution_ready_counts[key]}")
    else:
        lines.append("- no readiness execution-ready history was available")
    lines.extend(["", "## Recent Changes", ""])
    if entries:
        for item in entries[-limit:]:
            lines.append(
                "- "
                f"{item.get('created_at')} | op={item.get('operation')} | status={item.get('status')} | "
                f"diagnostics={item.get('diagnostics_status')} | next_phase={item.get('readiness_next_phase')} | "
                f"execution_ready={item.get('readiness_execution_ready')}"
            )
    else:
        lines.append("- no execution gap history entries available")
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
