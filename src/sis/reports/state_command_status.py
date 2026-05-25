from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order
from sis.storage.jsonl_store import write_json


def _recommended_read_order() -> list[str]:
    return recommended_read_order(
        [
            "data/ops/operations_dashboard_summary.json",
            "data/ops/current_state_index.json",
            "data/ops/readiness_snapshot.json",
            "data/ops/phase_gate_review_summary.json",
        ]
    )


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "state_command_report": str(out_path),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
    }


def _write_report(
    *,
    title: str,
    summary: dict[str, object],
    detail_lines: list[str],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    quick_navigation = summary.get("quick_navigation")
    related_reports = summary.get("related_reports")
    lines = [f"# {title}", ""]
    if isinstance(quick_navigation, dict) and quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if isinstance(related_reports, dict) and related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(["## Overview", "", *detail_lines, "", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in _recommended_read_order())
    lines.append("")
    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text


def build_daemon_manifest_report(
    *,
    manifest: dict[str, object],
    manifest_path: str,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary: dict[str, object] = {
        **manifest,
        "daemon_manifest_path": manifest_path,
        "daemon_manifest_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    notes = summary.get("notes")
    detail_notes = ",".join(notes) if isinstance(notes, list) else str(notes)
    return _write_report(
        title="Daemon Manifest",
        summary=summary,
        detail_lines=[
            f"- run_id: {summary.get('run_id')}",
            f"- created_at: {summary.get('created_at')}",
            f"- mode: {summary.get('mode')}",
            f"- command: {summary.get('command')}",
            f"- state_store_path: {summary.get('state_store_path')}",
            f"- notes: {detail_notes}",
            f"- daemon_manifest_path: {summary.get('daemon_manifest_path')}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_daemon_loop_report(
    *,
    snapshot: dict[str, object],
    snapshot_path: str,
    event_log_path: str,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    latest_event = snapshot.get("latest_event") if isinstance(snapshot.get("latest_event"), dict) else {}
    summary: dict[str, object] = {
        "run_id": snapshot.get("run_id"),
        "created_at": snapshot.get("created_at"),
        "mode": snapshot.get("mode"),
        "command": snapshot.get("command"),
        "status": snapshot.get("status"),
        "cycles_requested": snapshot.get("cycles_requested"),
        "cycles_completed": snapshot.get("cycles_completed"),
        "every_minutes": snapshot.get("every_minutes"),
        "sleep_seconds": snapshot.get("sleep_seconds"),
        "daemon_manifest_path": snapshot.get("daemon_manifest_path"),
        "daemon_loop_path": snapshot_path,
        "daemon_loop_events_path": event_log_path,
        "latest_event_status": latest_event.get("status"),
        "latest_event_exit_code": latest_event.get("exit_code"),
        "daemon_loop_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="Daemon Loop",
        summary=summary,
        detail_lines=[
            f"- run_id: {summary.get('run_id')}",
            f"- mode: {summary.get('mode')}",
            f"- command: {summary.get('command')}",
            f"- status: {summary.get('status')}",
            f"- cycles_requested: {summary.get('cycles_requested')}",
            f"- cycles_completed: {summary.get('cycles_completed')}",
            f"- every_minutes: {summary.get('every_minutes')}",
            f"- latest_event_status: {summary.get('latest_event_status')}",
            f"- latest_event_exit_code: {summary.get('latest_event_exit_code')}",
            f"- daemon_loop_path: {summary.get('daemon_loop_path')}",
            f"- daemon_loop_events_path: {summary.get('daemon_loop_events_path')}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_state_export_report(
    *,
    snapshot: dict[str, object],
    snapshot_path: str,
    state_store_path: str,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary: dict[str, object] = {
        "snapshot_path": snapshot_path,
        "state_store_path": state_store_path,
        "paper_positions_present": snapshot.get("paper_positions") is not None,
        "paper_last_run_present": snapshot.get("paper_last_run") is not None,
        "latest_reconciliation_present": snapshot.get("latest_reconciliation") is not None,
        "audit_overall_status": snapshot.get("audit_overall_status"),
        "audit_latest_operation": snapshot.get("audit_latest_operation"),
        "phase_gate_decision": snapshot.get("phase_gate_decision"),
        "phase2_entry_allowed": snapshot.get("phase2_entry_allowed"),
        "phase2_entry_reason": snapshot.get("phase2_entry_reason"),
        "phase_gate_reason": snapshot.get("phase_gate_reason"),
        "phase_gate_strict_validation_passed": snapshot.get("phase_gate_strict_validation_passed"),
        "phase_gate_checked_files": snapshot.get("phase_gate_checked_files"),
        "readiness_next_phase_candidate": snapshot.get("readiness_next_phase_candidate"),
        "readiness_execution_ready": snapshot.get("readiness_execution_ready"),
        "execution_drift_overview_status": snapshot.get("execution_drift_overview_status"),
        "state_export_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="State Export Snapshot",
        summary=summary,
        detail_lines=[
            f"- snapshot_path: {summary.get('snapshot_path')}",
            f"- state_store_path: {summary.get('state_store_path')}",
            f"- paper_positions_present: {summary.get('paper_positions_present')}",
            f"- paper_last_run_present: {summary.get('paper_last_run_present')}",
            f"- latest_reconciliation_present: {summary.get('latest_reconciliation_present')}",
            f"- audit_overall_status: {summary.get('audit_overall_status')}",
            f"- audit_latest_operation: {summary.get('audit_latest_operation')}",
            f"- phase_gate_decision: {summary.get('phase_gate_decision')}",
            f"- phase_gate_reason: {summary.get('phase_gate_reason')}",
            f"- phase_gate_strict_validation_passed: {summary.get('phase_gate_strict_validation_passed')}",
            f"- readiness_next_phase_candidate: {summary.get('readiness_next_phase_candidate')}",
            f"- readiness_execution_ready: {summary.get('readiness_execution_ready')}",
            f"- execution_drift_overview_status: {summary.get('execution_drift_overview_status')}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_state_restore_report(
    *,
    snapshot: dict[str, object],
    snapshot_path: str,
    state_store_path: str,
    restored: bool,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary: dict[str, object] = {
        "restored": restored,
        "snapshot_path": snapshot_path,
        "state_store_path": state_store_path,
        "paper_positions_present": snapshot.get("paper_positions") is not None,
        "paper_last_run_present": snapshot.get("paper_last_run") is not None,
        "latest_reconciliation_present": snapshot.get("latest_reconciliation") is not None,
        "audit_overall_status": snapshot.get("audit_overall_status"),
        "audit_latest_operation": snapshot.get("audit_latest_operation"),
        "phase_gate_decision": snapshot.get("phase_gate_decision"),
        "phase2_entry_allowed": snapshot.get("phase2_entry_allowed"),
        "phase2_entry_reason": snapshot.get("phase2_entry_reason"),
        "phase_gate_reason": snapshot.get("phase_gate_reason"),
        "phase_gate_strict_validation_passed": snapshot.get("phase_gate_strict_validation_passed"),
        "phase_gate_checked_files": snapshot.get("phase_gate_checked_files"),
        "readiness_next_phase_candidate": snapshot.get("readiness_next_phase_candidate"),
        "readiness_execution_ready": snapshot.get("readiness_execution_ready"),
        "execution_drift_overview_status": snapshot.get("execution_drift_overview_status"),
        "state_restore_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="State Restore Snapshot",
        summary=summary,
        detail_lines=[
            f"- restored: {summary.get('restored')}",
            f"- snapshot_path: {summary.get('snapshot_path')}",
            f"- state_store_path: {summary.get('state_store_path')}",
            f"- paper_positions_present: {summary.get('paper_positions_present')}",
            f"- paper_last_run_present: {summary.get('paper_last_run_present')}",
            f"- latest_reconciliation_present: {summary.get('latest_reconciliation_present')}",
            f"- audit_overall_status: {summary.get('audit_overall_status')}",
            f"- audit_latest_operation: {summary.get('audit_latest_operation')}",
            f"- phase_gate_decision: {summary.get('phase_gate_decision')}",
            f"- phase_gate_reason: {summary.get('phase_gate_reason')}",
            f"- phase_gate_strict_validation_passed: {summary.get('phase_gate_strict_validation_passed')}",
            f"- readiness_next_phase_candidate: {summary.get('readiness_next_phase_candidate')}",
            f"- readiness_execution_ready: {summary.get('readiness_execution_ready')}",
            f"- execution_drift_overview_status: {summary.get('execution_drift_overview_status')}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )
