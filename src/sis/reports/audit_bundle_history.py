from __future__ import annotations

from pathlib import Path

from sis.reports.audit_bundle_history_helpers import (
    latest_note_summary_fields as _latest_note_summary_fields,
)
from sis.reports.audit_bundle_history_helpers import quick_navigation as _quick_navigation
from sis.reports.audit_bundle_history_helpers import related_reports as _related_reports
from sis.reports.audit_bundle_history_helpers import report_path_fields as _report_path_fields
from sis.reports.audit_bundle_history_helpers import reports_dir as _reports_dir
from sis.reports.audit_bundle_history_helpers import summary_section_lines as _summary_section_lines
from sis.reports.loaders import normalized_summary
from sis.reports.summary_normalizers import (
    latest_execution_lineage_from_notes,
    execution_snapshot_flat_fields,
    normalize_execution_snapshot_summary,
)
from sis.storage.jsonl_store import read_jsonl, write_json


def build_audit_bundle_history_report(
    *,
    operation_chain_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations = (
        list(read_jsonl(operation_chain_path))
        if operation_chain_path and operation_chain_path.exists()
        else []
    )
    snapshots = [
        item for item in operations if str(item.get("operation")) == "audit_bundle_snapshot"
    ]
    execution = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)

    ok_count = sum(1 for item in snapshots if str(item.get("status")) == "ok")
    latest = snapshots[-1] if snapshots else {}
    latest_notes = latest.get("notes", []) if isinstance(latest, dict) else []
    latest_execution_lineage = latest_execution_lineage_from_notes(latest_notes)
    latest_note_fields = (
        _latest_note_summary_fields(latest_notes) if isinstance(latest_notes, list) else {}
    )
    reports_dir = _reports_dir(operation_chain_path)

    summary = {
        "snapshot_count": len(snapshots),
        "ok_count": ok_count,
        "latest_status": latest.get("status"),
        "latest_run_id": latest.get("run_id"),
        "latest_created_at": latest.get("created_at"),
        "execution_summary": execution,
        **latest_execution_lineage,
        **latest_note_fields,
        **execution_snapshot_fields,
        **_report_path_fields(out_path=out_path, reports_dir=reports_dir),
    }
    quick_navigation = _quick_navigation(summary)
    related_reports = _related_reports(summary)
    latest_phase_gate_issue_previews_raw = summary.get("latest_phase_gate_issue_previews")
    latest_phase_gate_issue_previews: list[object] = (
        list(latest_phase_gate_issue_previews_raw)
        if isinstance(latest_phase_gate_issue_previews_raw, list)
        else []
    )
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports

    lines = [
        "# Audit Bundle History Report",
        "",
        *_summary_section_lines(summary),
    ]
    lines.extend(["## Quick Navigation", ""])
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in related_reports.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    if latest_phase_gate_issue_previews:
        lines.extend(["## Latest Phase Gate Issue Preview", ""])
        lines.extend(f"- {item}" for item in latest_phase_gate_issue_previews)
        lines.append("")

    if snapshots:
        lines.extend(
            [
                "## Recent Snapshots",
                "",
            ]
        )
        for item in snapshots[-5:]:
            notes = item.get("notes", [])
            notes_text = ", ".join(str(x) for x in notes) if isinstance(notes, list) else ""
            lines.append(
                f"- {item.get('created_at')} | status={item.get('status')} | run_id={item.get('run_id')} | {notes_text}"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "## No Snapshots",
                "",
                "- no audit_bundle_snapshot entries were available in the operation chain",
                "",
            ]
        )

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
