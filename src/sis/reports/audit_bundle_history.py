from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    normalize_execution_snapshot_summary,
    execution_snapshot_flat_fields,
    phase_gate_issue_note_previews,
)
from sis.storage.jsonl_store import read_json, read_jsonl, write_json


def _note_value(notes: list[object], prefix: str) -> str | None:
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return None


def _note_values(notes: list[object], prefix: str) -> list[str]:
    values: list[str] = []
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            values.append(text.removeprefix(prefix))
    return values


def build_audit_bundle_history_report(
    *,
    operation_chain_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations = list(read_jsonl(operation_chain_path)) if operation_chain_path and operation_chain_path.exists() else []
    snapshots = [item for item in operations if str(item.get("operation")) == "audit_bundle_snapshot"]
    execution = normalize_execution_snapshot_summary(
        read_json(execution_snapshot_summary_path)
        if execution_snapshot_summary_path and execution_snapshot_summary_path.exists()
        else {}
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)

    ok_count = sum(1 for item in snapshots if str(item.get("status")) == "ok")
    latest = snapshots[-1] if snapshots else {}
    latest_notes = latest.get("notes", []) if isinstance(latest, dict) else []

    summary = {
        "snapshot_count": len(snapshots),
        "ok_count": ok_count,
        "latest_status": latest.get("status"),
        "latest_run_id": latest.get("run_id"),
        "latest_created_at": latest.get("created_at"),
        "execution_summary": execution,
        "latest_execution_drift_overview_summary": {
            "execution_drift_overview_status": (
                _note_value(latest_notes, "execution_drift_overview_status=")
                if isinstance(latest_notes, list)
                else None
            ),
            "execution_drift_overview_diagnostics_alignment_match": (
                _note_value(latest_notes, "execution_drift_overview_diagnostics_alignment_match=")
                if isinstance(latest_notes, list)
                else None
            ),
            "execution_drift_overview_state_comparison_mismatching_count": (
                _note_value(latest_notes, "execution_drift_overview_state_comparison_mismatching_count=")
                if isinstance(latest_notes, list)
                else None
            ),
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
                _note_value(
                    latest_notes,
                    "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
                )
                if isinstance(latest_notes, list)
                else None
            ),
        },
        "latest_execution_gap_history_summary": {
            "execution_gap_history_latest_status": (
                _note_value(latest_notes, "execution_gap_history_latest_status=")
                if isinstance(latest_notes, list)
                else None
            ),
            "execution_gap_history_latest_diagnostics_status": (
                _note_value(latest_notes, "execution_gap_history_latest_diagnostics_status=")
                if isinstance(latest_notes, list)
                else None
            ),
        },
        "latest_execution_state_comparison_summary": {
            "execution_state_comparison_latest_status_match": (
                _note_value(latest_notes, "execution_state_comparison_latest_status_match=")
                if isinstance(latest_notes, list)
                else None
            ),
            "execution_state_comparison_mismatching_count": (
                _note_value(latest_notes, "execution_state_comparison_mismatching_count=")
                if isinstance(latest_notes, list)
                else None
            ),
        },
        "latest_readiness_summary": {
            "readiness_next_phase_candidate": (
                _note_value(latest_notes, "readiness_next_phase=")
                if isinstance(latest_notes, list)
                else None
            ),
            "readiness_execution_ready": (
                _note_value(latest_notes, "readiness_execution_ready=")
                if isinstance(latest_notes, list)
                else None
            ),
        },
        "latest_phase_gate_summary": {
            "phase_gate_decision": (
                _note_value(latest_notes, "phase_gate_decision=")
                if isinstance(latest_notes, list)
                else None
            ),
            "phase2_entry_allowed": (
                _note_value(latest_notes, "phase2_entry_allowed=")
                if isinstance(latest_notes, list)
                else None
            ),
            "phase_gate_reason": (
                _note_value(latest_notes, "phase_gate_reason=")
                if isinstance(latest_notes, list)
                else None
            ),
            "phase_gate_strict_validation_passed": (
                _note_value(latest_notes, "phase_gate_strict_validation_passed=")
                if isinstance(latest_notes, list)
                else None
            ),
            "phase_gate_strict_validation_issue_count": (
                _note_value(latest_notes, "phase_gate_strict_validation_issue_count=")
                if isinstance(latest_notes, list)
                else None
            ),
            "phase_gate_checked_files": (
                _note_value(latest_notes, "phase_gate_checked_files=")
                if isinstance(latest_notes, list)
                else None
            ),
            "phase_gate_review_report_path": (
                _note_value(latest_notes, "phase_gate_review_report_path=")
                if isinstance(latest_notes, list)
                else None
            ),
            "phase_gate_strict_validation_issues": (
                phase_gate_issue_note_previews(latest_notes) if isinstance(latest_notes, list) else []
            ),
        },
        "latest_execution_gap_history_status": (
            _note_value(latest_notes, "execution_gap_history_latest_status=") if isinstance(latest_notes, list) else None
        ),
        "latest_execution_drift_overview_status": (
            _note_value(latest_notes, "execution_drift_overview_status=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_execution_drift_overview_diagnostics_alignment_match": (
            _note_value(latest_notes, "execution_drift_overview_diagnostics_alignment_match=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_execution_drift_overview_state_comparison_mismatching_count": (
            _note_value(latest_notes, "execution_drift_overview_state_comparison_mismatching_count=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            _note_value(
                latest_notes,
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
            )
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_execution_gap_history_diagnostics_status": (
            _note_value(latest_notes, "execution_gap_history_latest_diagnostics_status=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_execution_state_comparison_status_match": (
            _note_value(latest_notes, "execution_state_comparison_latest_status_match=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_execution_state_comparison_mismatching_count": (
            _note_value(latest_notes, "execution_state_comparison_mismatching_count=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_readiness_next_phase": (
            _note_value(latest_notes, "readiness_next_phase=") if isinstance(latest_notes, list) else None
        ),
        "latest_readiness_execution_ready": (
            _note_value(latest_notes, "readiness_execution_ready=") if isinstance(latest_notes, list) else None
        ),
        "latest_phase_gate_decision": (
            _note_value(latest_notes, "phase_gate_decision=") if isinstance(latest_notes, list) else None
        ),
        "latest_phase2_entry_allowed": (
            _note_value(latest_notes, "phase2_entry_allowed=") if isinstance(latest_notes, list) else None
        ),
        "latest_phase_gate_reason": (
            _note_value(latest_notes, "phase_gate_reason=") if isinstance(latest_notes, list) else None
        ),
        "latest_phase_gate_strict_validation_passed": (
            _note_value(latest_notes, "phase_gate_strict_validation_passed=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase_gate_strict_validation_issue_count": (
            _note_value(latest_notes, "phase_gate_strict_validation_issue_count=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase_gate_checked_files": (
            _note_value(latest_notes, "phase_gate_checked_files=") if isinstance(latest_notes, list) else None
        ),
        "latest_phase_gate_review_report_path": (
            _note_value(latest_notes, "phase_gate_review_report_path=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase_gate_issue_previews": (
            phase_gate_issue_note_previews(latest_notes) if isinstance(latest_notes, list) else []
        ),
        **execution_snapshot_fields,
    }

    lines = [
        "# Audit Bundle History Report",
        "",
        "## Summary",
        "",
        f"- snapshot_count: {summary['snapshot_count']}",
        f"- ok_count: {summary['ok_count']}",
        f"- latest_status: {summary['latest_status']}",
        f"- latest_run_id: {summary['latest_run_id']}",
        f"- latest_created_at: {summary['latest_created_at']}",
        f"- latest_execution_gap_history_status: {summary['latest_execution_gap_history_status']}",
        f"- latest_execution_drift_overview_status: {summary['latest_execution_drift_overview_status']}",
        (
            "- latest_execution_drift_overview_diagnostics_alignment_match: "
            f"{summary['latest_execution_drift_overview_diagnostics_alignment_match']}"
        ),
        (
            "- latest_execution_drift_overview_state_comparison_mismatching_count: "
            f"{summary['latest_execution_drift_overview_state_comparison_mismatching_count']}"
        ),
        (
            "- latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
        ),
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
        f"- latest_phase_gate_decision: {summary['latest_phase_gate_decision']}",
        f"- latest_phase2_entry_allowed: {summary['latest_phase2_entry_allowed']}",
        f"- latest_phase_gate_reason: {summary['latest_phase_gate_reason']}",
        f"- latest_phase_gate_strict_validation_passed: {summary['latest_phase_gate_strict_validation_passed']}",
        (
            "- latest_phase_gate_strict_validation_issue_count: "
            f"{summary['latest_phase_gate_strict_validation_issue_count']}"
        ),
        f"- latest_phase_gate_checked_files: {summary['latest_phase_gate_checked_files']}",
        f"- latest_phase_gate_review_report_path: {summary['latest_phase_gate_review_report_path']}",
        f"- execution_overall_status: {summary['execution_overall_status']}",
        f"- execution_venue_count: {summary['execution_venue_count']}",
        "",
    ]
    if summary["latest_phase_gate_issue_previews"]:
        lines.extend(["## Latest Phase Gate Issue Preview", ""])
        lines.extend(f"- {item}" for item in summary["latest_phase_gate_issue_previews"])
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
