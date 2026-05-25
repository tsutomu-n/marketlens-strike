from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary
from sis.reports.summary_normalizers import (
    latest_execution_lineage_from_notes,
    execution_snapshot_flat_fields,
    phase_gate_issue_note_previews,
    normalize_execution_snapshot_summary,
)
from sis.storage.jsonl_store import read_jsonl, write_json


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


def _reports_dir(operation_chain_path: Path | None) -> Path | None:
    if operation_chain_path is None:
        return None
    base = (
        operation_chain_path.parent.parent
        if operation_chain_path.parent.name == "ops"
        else operation_chain_path.parent
    )
    return base / "reports"


def _quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("audit_bundle_history_report", summary.get("audit_bundle_history_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("audit_bundle_history_report", summary.get("audit_bundle_history_report_path")),
        ("audit_timeline_report", summary.get("audit_timeline_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("audit_bundle_report", summary.get("audit_bundle_report_path")),
        ("operations_audit_pack_report", summary.get("operations_audit_pack_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_audit_bundle_history_report(
    *,
    operation_chain_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations = list(read_jsonl(operation_chain_path)) if operation_chain_path and operation_chain_path.exists() else []
    snapshots = [item for item in operations if str(item.get("operation")) == "audit_bundle_snapshot"]
    execution = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)

    ok_count = sum(1 for item in snapshots if str(item.get("status")) == "ok")
    latest = snapshots[-1] if snapshots else {}
    latest_notes = latest.get("notes", []) if isinstance(latest, dict) else []
    latest_execution_lineage = latest_execution_lineage_from_notes(latest_notes)
    latest_remediation_planner_status = (
        _note_value(latest_notes, "planner_status=") if isinstance(latest_notes, list) else None
    )
    latest_remediation_planner_next_best_command = (
        _note_value(latest_notes, "next_best_command=") if isinstance(latest_notes, list) else None
    )
    latest_remediation_planner_feedback_priority_reason = (
        _note_value(latest_notes, "next_feedback_priority_reason=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_execution_plan_status = (
        _note_value(latest_notes, "execution_plan_status=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_execution_plan_next_action_command = (
        _note_value(latest_notes, "next_action_command=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_execution_plan_feedback_priority_reason = (
        _note_value(latest_notes, "next_action_feedback_priority_reason=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_session_status = (
        _note_value(latest_notes, "session_status=") if isinstance(latest_notes, list) else None
    )
    latest_remediation_session_next_pending_command = (
        _note_value(latest_notes, "next_pending_command=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_session_feedback_priority_reason = (
        _note_value(latest_notes, "next_pending_feedback_priority_reason=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_checkpoint_status = (
        _note_value(latest_notes, "checkpoint_status=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_checkpoint_next_action_command = (
        _note_value(latest_notes, "next_action_command=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_checkpoint_feedback_priority_reason = (
        _note_value(latest_notes, "next_action_feedback_priority_reason=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_scoreboard_status = (
        _note_value(latest_notes, "scoreboard_status=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_scoreboard_next_action_command = (
        _note_value(latest_notes, "next_action_command=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_remediation_scoreboard_feedback_priority_reason = (
        _note_value(latest_notes, "next_action_feedback_priority_reason=")
        if isinstance(latest_notes, list)
        else None
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
        "latest_remediation_planner_status": latest_remediation_planner_status,
        "latest_remediation_planner_next_best_command": latest_remediation_planner_next_best_command,
        "latest_remediation_planner_feedback_priority_reason": (
            latest_remediation_planner_feedback_priority_reason
        ),
        "latest_remediation_execution_plan_status": latest_remediation_execution_plan_status,
        "latest_remediation_execution_plan_next_action_command": (
            latest_remediation_execution_plan_next_action_command
        ),
        "latest_remediation_execution_plan_feedback_priority_reason": (
            latest_remediation_execution_plan_feedback_priority_reason
        ),
        "latest_remediation_session_status": latest_remediation_session_status,
        "latest_remediation_session_next_pending_command": latest_remediation_session_next_pending_command,
        "latest_remediation_session_feedback_priority_reason": (
            latest_remediation_session_feedback_priority_reason
        ),
        "latest_remediation_checkpoint_status": latest_remediation_checkpoint_status,
        "latest_remediation_checkpoint_next_action_command": (
            latest_remediation_checkpoint_next_action_command
        ),
        "latest_remediation_checkpoint_feedback_priority_reason": (
            latest_remediation_checkpoint_feedback_priority_reason
        ),
        "latest_remediation_scoreboard_status": latest_remediation_scoreboard_status,
        "latest_remediation_scoreboard_next_action_command": (
            latest_remediation_scoreboard_next_action_command
        ),
        "latest_remediation_scoreboard_feedback_priority_reason": (
            latest_remediation_scoreboard_feedback_priority_reason
        ),
        **execution_snapshot_fields,
        "audit_bundle_history_report_path": str(out_path) if out_path is not None else None,
        "audit_timeline_report_path": str(reports_dir / "audit_timeline.md") if reports_dir else None,
        "audit_dashboard_report_path": str(reports_dir / "audit_dashboard.md") if reports_dir else None,
        "audit_bundle_report_path": str(reports_dir / "audit_bundle_manifest.md") if reports_dir else None,
        "operations_audit_pack_report_path": (
            str(reports_dir / "operations_audit_pack.md") if reports_dir else None
        ),
        "current_state_index_report_path": str(reports_dir / "current_state_index.md") if reports_dir else None,
        "readiness_snapshot_report_path": str(reports_dir / "readiness_snapshot.md") if reports_dir else None,
        "remediation_scoreboard_report_path": (
            str(reports_dir / "remediation_scoreboard.md") if reports_dir else None
        ),
    }
    summary["quick_navigation"] = _quick_navigation(summary)
    summary["related_reports"] = _related_reports(summary)

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
    for key, value in summary["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in summary["related_reports"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
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
