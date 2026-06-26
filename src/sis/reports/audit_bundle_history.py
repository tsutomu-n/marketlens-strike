from __future__ import annotations

from pathlib import Path

from sis.reports.audit_bundle_history_helpers import (
    latest_note_summary_fields as _latest_note_summary_fields,
)
from sis.reports.audit_bundle_history_helpers import quick_navigation as _quick_navigation
from sis.reports.audit_bundle_history_helpers import related_reports as _related_reports
from sis.reports.audit_bundle_history_helpers import reports_dir as _reports_dir
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
        "audit_bundle_history_report_path": str(out_path) if out_path is not None else None,
        "audit_timeline_report_path": str(reports_dir / "audit_timeline.md")
        if reports_dir
        else None,
        "audit_dashboard_report_path": str(reports_dir / "audit_dashboard.md")
        if reports_dir
        else None,
        "audit_bundle_report_path": str(reports_dir / "audit_bundle_manifest.md")
        if reports_dir
        else None,
        "operations_audit_pack_report_path": (
            str(reports_dir / "operations_audit_pack.md") if reports_dir else None
        ),
        "current_state_index_report_path": str(reports_dir / "current_state_index.md")
        if reports_dir
        else None,
        "readiness_snapshot_report_path": str(reports_dir / "readiness_snapshot.md")
        if reports_dir
        else None,
        "remediation_scoreboard_report_path": (
            str(reports_dir / "remediation_scoreboard.md") if reports_dir else None
        ),
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
        "## Summary",
        "",
        f"- snapshot_count: {summary['snapshot_count']}",
        f"- ok_count: {summary['ok_count']}",
        f"- latest_status: {summary['latest_status']}",
        f"- latest_run_id: {summary['latest_run_id']}",
        f"- latest_created_at: {summary['latest_created_at']}",
        f"- latest_execution_overall_status: {summary['latest_execution_overall_status']}",
        f"- latest_execution_venue_count: {summary['latest_execution_venue_count']}",
        (
            "- latest_execution_comparison_all_registries_present: "
            f"{summary['latest_execution_comparison_all_registries_present']}"
        ),
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
        f"- latest_remediation_planner_status: {summary['latest_remediation_planner_status']}",
        f"- latest_remediation_planner_next_best_command: {summary['latest_remediation_planner_next_best_command']}",
        f"- latest_remediation_planner_feedback_priority_reason: {summary['latest_remediation_planner_feedback_priority_reason']}",
        f"- latest_remediation_execution_plan_status: {summary['latest_remediation_execution_plan_status']}",
        f"- latest_remediation_execution_plan_next_action_command: {summary['latest_remediation_execution_plan_next_action_command']}",
        (
            "- latest_remediation_execution_plan_feedback_priority_reason: "
            f"{summary['latest_remediation_execution_plan_feedback_priority_reason']}"
        ),
        f"- latest_remediation_session_status: {summary['latest_remediation_session_status']}",
        f"- latest_remediation_session_next_pending_command: {summary['latest_remediation_session_next_pending_command']}",
        f"- latest_remediation_session_feedback_priority_reason: {summary['latest_remediation_session_feedback_priority_reason']}",
        f"- latest_remediation_checkpoint_status: {summary['latest_remediation_checkpoint_status']}",
        f"- latest_remediation_checkpoint_next_action_command: {summary['latest_remediation_checkpoint_next_action_command']}",
        (
            "- latest_remediation_checkpoint_feedback_priority_reason: "
            f"{summary['latest_remediation_checkpoint_feedback_priority_reason']}"
        ),
        f"- latest_remediation_scoreboard_status: {summary['latest_remediation_scoreboard_status']}",
        f"- latest_remediation_scoreboard_next_action_command: {summary['latest_remediation_scoreboard_next_action_command']}",
        (
            "- latest_remediation_scoreboard_feedback_priority_reason: "
            f"{summary['latest_remediation_scoreboard_feedback_priority_reason']}"
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
