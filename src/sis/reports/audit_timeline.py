from __future__ import annotations

from pathlib import Path
from typing import cast

from sis.reports.summary_normalizers import (
    latest_execution_lineage_from_notes,
    phase_gate_issue_note_previews,
)
from sis.storage.jsonl_store import read_jsonl, write_json


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
        ("audit_timeline_report", summary.get("audit_timeline_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("audit_timeline_report", summary.get("audit_timeline_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("operations_dashboard_report", summary.get("operations_dashboard_report_path")),
        ("operations_audit_pack_report", summary.get("operations_audit_pack_report_path")),
        ("audit_bundle_report", summary.get("audit_bundle_report_path")),
        ("audit_bundle_history_report", summary.get("audit_bundle_history_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _note_value(notes: list[object], prefix: str) -> str | None:
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return None


def _note_counts(items: list[dict[str, object]], prefix: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        notes = item.get("notes", [])
        if not isinstance(notes, list):
            continue
        value = _note_value(cast(list[object], notes), prefix)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _note_values(notes: list[object], prefix: str) -> list[str]:
    values: list[str] = []
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            values.append(text.removeprefix(prefix))
    return values


def _latest_operation_entry(items: list[dict[str, object]], operation: str) -> dict[str, object]:
    for item in reversed(items):
        if str(item.get("operation")) == operation:
            return item
    return {}


def _latest_note_from_operation(
    items: list[dict[str, object]], operation: str, prefix: str
) -> str | None:
    latest = _latest_operation_entry(items, operation)
    notes = latest.get("notes", []) if isinstance(latest, dict) else []
    return _note_value(cast(list[object], notes), prefix) if isinstance(notes, list) else None


def build_audit_timeline_report(
    *,
    operation_chain_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
    limit: int = 20,
) -> str:
    operations = (
        list(read_jsonl(operation_chain_path))
        if operation_chain_path and operation_chain_path.exists()
        else []
    )
    audit_ops = [
        item
        for item in operations
        if str(item.get("operation"))
        in {"operations_snapshot", "operations_audit_snapshot", "audit_bundle_snapshot"}
    ]
    recent = audit_ops[-limit:]

    counts: dict[str, int] = {}
    for item in audit_ops:
        operation = str(item.get("operation", "unknown"))
        counts[operation] = counts.get(operation, 0) + 1

    diagnostics_status_counts = _note_counts(audit_ops, "execution_diagnostics_status=")
    drift_overview_status_counts = _note_counts(audit_ops, "execution_drift_overview_status=")
    drift_overview_diagnostics_alignment_counts = _note_counts(
        audit_ops, "execution_drift_overview_diagnostics_alignment_match="
    )
    drift_overview_state_comparison_mismatching_count_values = _note_counts(
        audit_ops, "execution_drift_overview_state_comparison_mismatching_count="
    )
    drift_overview_snapshot_drift_mismatching_snapshot_count_values = _note_counts(
        audit_ops, "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
    )
    gap_history_status_counts = _note_counts(audit_ops, "execution_gap_history_latest_status=")
    gap_history_diagnostics_status_counts = _note_counts(
        audit_ops, "execution_gap_history_latest_diagnostics_status="
    )
    state_comparison_status_match_counts = _note_counts(
        audit_ops, "execution_state_comparison_latest_status_match="
    )
    state_comparison_mismatching_count_values = _note_counts(
        audit_ops, "execution_state_comparison_mismatching_count="
    )
    readiness_next_phase_counts = _note_counts(audit_ops, "readiness_next_phase=")
    readiness_execution_ready_counts = _note_counts(audit_ops, "readiness_execution_ready=")
    latest = recent[-1] if recent else {}
    latest_notes = latest.get("notes", []) if isinstance(latest, dict) else []
    latest_phase_gate_issue_previews = (
        phase_gate_issue_note_previews(latest_notes) if isinstance(latest_notes, list) else []
    )
    phase_gate_decision_counts = _note_counts(audit_ops, "phase_gate_decision=")
    phase2_entry_allowed_counts = _note_counts(audit_ops, "phase2_entry_allowed=")
    phase_gate_reason_counts = _note_counts(audit_ops, "phase_gate_reason=")
    phase_gate_strict_validation_passed_counts = _note_counts(
        audit_ops, "phase_gate_strict_validation_passed="
    )
    phase_gate_strict_validation_issue_count_values = _note_counts(
        audit_ops, "phase_gate_strict_validation_issue_count="
    )
    phase_gate_checked_files_values = _note_counts(audit_ops, "phase_gate_checked_files=")
    latest_execution_lineage = latest_execution_lineage_from_notes(latest_notes)
    latest_remediation_planner_status = _latest_note_from_operation(
        operations, "remediation_planner_dry_run", "planner_status="
    )
    latest_remediation_planner_next_best_command = _latest_note_from_operation(
        operations, "remediation_planner_dry_run", "next_best_command="
    )
    latest_remediation_planner_feedback_priority_reason = _latest_note_from_operation(
        operations, "remediation_planner_dry_run", "next_feedback_priority_reason="
    )
    latest_remediation_execution_plan_status = _latest_note_from_operation(
        operations, "remediation_execution_plan_dry_run", "execution_plan_status="
    )
    latest_remediation_execution_plan_next_action_command = _latest_note_from_operation(
        operations, "remediation_execution_plan_dry_run", "next_action_command="
    )
    latest_remediation_execution_plan_feedback_priority_reason = _latest_note_from_operation(
        operations, "remediation_execution_plan_dry_run", "next_action_feedback_priority_reason="
    )
    latest_remediation_session_status = _latest_note_from_operation(
        operations, "remediation_session_dry_run", "session_status="
    )
    latest_remediation_session_next_pending_command = _latest_note_from_operation(
        operations, "remediation_session_dry_run", "next_pending_command="
    )
    latest_remediation_session_feedback_priority_reason = _latest_note_from_operation(
        operations, "remediation_session_dry_run", "next_pending_feedback_priority_reason="
    )
    latest_remediation_checkpoint_status = _latest_note_from_operation(
        operations, "remediation_session_checkpoint", "checkpoint_status="
    )
    latest_remediation_checkpoint_next_action_command = _latest_note_from_operation(
        operations, "remediation_session_checkpoint", "next_action_command="
    )
    latest_remediation_checkpoint_feedback_priority_reason = _latest_note_from_operation(
        operations, "remediation_session_checkpoint", "next_action_feedback_priority_reason="
    )
    latest_remediation_scoreboard_status = _latest_note_from_operation(
        operations, "remediation_scoreboard", "scoreboard_status="
    )
    latest_remediation_scoreboard_next_action_command = _latest_note_from_operation(
        operations, "remediation_scoreboard", "next_action_command="
    )
    latest_remediation_scoreboard_feedback_priority_reason = _latest_note_from_operation(
        operations, "remediation_scoreboard", "next_action_feedback_priority_reason="
    )
    reports_dir = _reports_dir(operation_chain_path)

    summary = {
        "audit_entry_count": len(audit_ops),
        "recent_count": len(recent),
        "latest_operation": latest.get("operation") if latest else None,
        "latest_status": latest.get("status") if latest else None,
        **latest_execution_lineage,
        "latest_execution_diagnostics_summary": {
            "execution_diagnostics_status": (
                _note_value(latest_notes, "execution_diagnostics_status=")
                if isinstance(latest_notes, list)
                else None
            )
        },
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
                _note_value(
                    latest_notes, "execution_drift_overview_state_comparison_mismatching_count="
                )
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
                phase_gate_issue_note_previews(latest_notes)
                if isinstance(latest_notes, list)
                else []
            ),
        },
        "operation_counts": counts,
        "latest_execution_diagnostics_status": (
            _note_value(latest_notes, "execution_diagnostics_status=")
            if isinstance(latest_notes, list)
            else None
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
            _note_value(
                latest_notes, "execution_drift_overview_state_comparison_mismatching_count="
            )
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
        "latest_execution_gap_history_status": (
            _note_value(latest_notes, "execution_gap_history_latest_status=")
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
            _note_value(latest_notes, "readiness_next_phase=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_readiness_execution_ready": (
            _note_value(latest_notes, "readiness_execution_ready=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase_gate_decision": (
            _note_value(latest_notes, "phase_gate_decision=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase2_entry_allowed": (
            _note_value(latest_notes, "phase2_entry_allowed=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase_gate_reason": (
            _note_value(latest_notes, "phase_gate_reason=")
            if isinstance(latest_notes, list)
            else None
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
            _note_value(latest_notes, "phase_gate_checked_files=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase_gate_review_report_path": (
            _note_value(latest_notes, "phase_gate_review_report_path=")
            if isinstance(latest_notes, list)
            else None
        ),
        "latest_phase_gate_issue_previews": (latest_phase_gate_issue_previews),
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
        "diagnostics_status_counts": diagnostics_status_counts,
        "drift_overview_status_counts": drift_overview_status_counts,
        "drift_overview_diagnostics_alignment_counts": drift_overview_diagnostics_alignment_counts,
        "drift_overview_state_comparison_mismatching_count_values": (
            drift_overview_state_comparison_mismatching_count_values
        ),
        "drift_overview_snapshot_drift_mismatching_snapshot_count_values": (
            drift_overview_snapshot_drift_mismatching_snapshot_count_values
        ),
        "gap_history_status_counts": gap_history_status_counts,
        "gap_history_diagnostics_status_counts": gap_history_diagnostics_status_counts,
        "state_comparison_status_match_counts": state_comparison_status_match_counts,
        "state_comparison_mismatching_count_values": state_comparison_mismatching_count_values,
        "readiness_next_phase_counts": readiness_next_phase_counts,
        "readiness_execution_ready_counts": readiness_execution_ready_counts,
        "phase_gate_decision_counts": phase_gate_decision_counts,
        "phase2_entry_allowed_counts": phase2_entry_allowed_counts,
        "phase_gate_reason_counts": phase_gate_reason_counts,
        "phase_gate_strict_validation_passed_counts": phase_gate_strict_validation_passed_counts,
        "phase_gate_strict_validation_issue_count_values": phase_gate_strict_validation_issue_count_values,
        "phase_gate_checked_files_values": phase_gate_checked_files_values,
        "audit_timeline_report_path": str(out_path) if out_path is not None else None,
        "audit_dashboard_report_path": str(reports_dir / "audit_dashboard.md")
        if reports_dir
        else None,
        "operations_dashboard_report_path": (
            str(reports_dir / "operations_dashboard.md") if reports_dir else None
        ),
        "operations_audit_pack_report_path": (
            str(reports_dir / "operations_audit_pack.md") if reports_dir else None
        ),
        "audit_bundle_report_path": (
            str(reports_dir / "audit_bundle_manifest.md") if reports_dir else None
        ),
        "audit_bundle_history_report_path": (
            str(reports_dir / "audit_bundle_history.md") if reports_dir else None
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
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports

    lines = [
        "# Audit Timeline Report",
        "",
        "## Summary",
        "",
        f"- audit_entry_count: {summary['audit_entry_count']}",
        f"- recent_count: {summary['recent_count']}",
        f"- latest_operation: {summary['latest_operation']}",
        f"- latest_status: {summary['latest_status']}",
        f"- latest_execution_overall_status: {summary['latest_execution_overall_status']}",
        f"- latest_execution_venue_count: {summary['latest_execution_venue_count']}",
        (
            "- latest_execution_comparison_all_registries_present: "
            f"{summary['latest_execution_comparison_all_registries_present']}"
        ),
        f"- latest_execution_diagnostics_status: {summary['latest_execution_diagnostics_status']}",
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
        f"- latest_execution_gap_history_status: {summary['latest_execution_gap_history_status']}",
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
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Related Reports",
            "",
        ]
    )
    for key, value in related_reports.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Remediation State",
            "",
            f"- latest_remediation_planner_status: {summary['latest_remediation_planner_status']}",
            f"- latest_remediation_planner_next_best_command: {summary['latest_remediation_planner_next_best_command']}",
            f"- latest_remediation_planner_feedback_priority_reason: {summary['latest_remediation_planner_feedback_priority_reason']}",
            f"- latest_remediation_execution_plan_status: {summary['latest_remediation_execution_plan_status']}",
            f"- latest_remediation_execution_plan_next_action_command: {summary['latest_remediation_execution_plan_next_action_command']}",
            f"- latest_remediation_execution_plan_feedback_priority_reason: {summary['latest_remediation_execution_plan_feedback_priority_reason']}",
            f"- latest_remediation_session_status: {summary['latest_remediation_session_status']}",
            f"- latest_remediation_session_next_pending_command: {summary['latest_remediation_session_next_pending_command']}",
            f"- latest_remediation_session_feedback_priority_reason: {summary['latest_remediation_session_feedback_priority_reason']}",
            f"- latest_remediation_checkpoint_status: {summary['latest_remediation_checkpoint_status']}",
            f"- latest_remediation_checkpoint_next_action_command: {summary['latest_remediation_checkpoint_next_action_command']}",
            f"- latest_remediation_checkpoint_feedback_priority_reason: {summary['latest_remediation_checkpoint_feedback_priority_reason']}",
            f"- latest_remediation_scoreboard_status: {summary['latest_remediation_scoreboard_status']}",
            f"- latest_remediation_scoreboard_next_action_command: {summary['latest_remediation_scoreboard_next_action_command']}",
            f"- latest_remediation_scoreboard_feedback_priority_reason: {summary['latest_remediation_scoreboard_feedback_priority_reason']}",
            "",
            "## Audit Entry Counts",
            "",
        ]
    )
    if latest_phase_gate_issue_previews:
        lines.extend(["## Latest Phase Gate Issue Preview", ""])
        lines.extend(f"- {item}" for item in latest_phase_gate_issue_previews)
        lines.append("")
    if counts:
        for key in sorted(counts):
            lines.append(f"- {key}: {counts[key]}")
    else:
        lines.append("- no audit snapshot entries were available")
    lines.append("")

    lines.extend(["## Diagnostics Status Counts", ""])
    if diagnostics_status_counts:
        for key in sorted(diagnostics_status_counts):
            lines.append(f"- {key}: {diagnostics_status_counts[key]}")
    else:
        lines.append("- no execution diagnostics notes were available")
    lines.append("")

    lines.extend(["## Drift Overview Status Counts", ""])
    if drift_overview_status_counts:
        for key in sorted(drift_overview_status_counts):
            lines.append(f"- {key}: {drift_overview_status_counts[key]}")
    else:
        lines.append("- no execution drift overview notes were available")
    lines.append("")

    lines.extend(["## Drift Overview Diagnostics Alignment Counts", ""])
    if drift_overview_diagnostics_alignment_counts:
        for key in sorted(drift_overview_diagnostics_alignment_counts):
            lines.append(f"- {key}: {drift_overview_diagnostics_alignment_counts[key]}")
    else:
        lines.append("- no execution drift overview alignment notes were available")
    lines.append("")

    lines.extend(["## Drift Overview State Comparison Mismatching Count Values", ""])
    if drift_overview_state_comparison_mismatching_count_values:
        for key in sorted(drift_overview_state_comparison_mismatching_count_values):
            lines.append(
                f"- {key}: {drift_overview_state_comparison_mismatching_count_values[key]}"
            )
    else:
        lines.append("- no execution drift overview state comparison mismatch notes were available")
    lines.append("")

    lines.extend(["## Drift Overview Snapshot Drift Mismatching Count Values", ""])
    if drift_overview_snapshot_drift_mismatching_snapshot_count_values:
        for key in sorted(drift_overview_snapshot_drift_mismatching_snapshot_count_values):
            lines.append(
                f"- {key}: {drift_overview_snapshot_drift_mismatching_snapshot_count_values[key]}"
            )
    else:
        lines.append("- no execution drift overview snapshot drift mismatch notes were available")
    lines.append("")

    lines.extend(["## Gap History Status Counts", ""])
    if gap_history_status_counts:
        for key in sorted(gap_history_status_counts):
            lines.append(f"- {key}: {gap_history_status_counts[key]}")
    else:
        lines.append("- no execution gap history status notes were available")
    lines.append("")

    lines.extend(["## Gap History Diagnostics Status Counts", ""])
    if gap_history_diagnostics_status_counts:
        for key in sorted(gap_history_diagnostics_status_counts):
            lines.append(f"- {key}: {gap_history_diagnostics_status_counts[key]}")
    else:
        lines.append("- no execution gap history diagnostics notes were available")
    lines.append("")

    lines.extend(["## State Comparison Status Match Counts", ""])
    if state_comparison_status_match_counts:
        for key in sorted(state_comparison_status_match_counts):
            lines.append(f"- {key}: {state_comparison_status_match_counts[key]}")
    else:
        lines.append("- no execution state comparison match notes were available")
    lines.append("")

    lines.extend(["## State Comparison Mismatching Count Values", ""])
    if state_comparison_mismatching_count_values:
        for key in sorted(state_comparison_mismatching_count_values):
            lines.append(f"- {key}: {state_comparison_mismatching_count_values[key]}")
    else:
        lines.append("- no execution state comparison mismatch notes were available")
    lines.append("")

    lines.extend(["## Readiness Next Phase Counts", ""])
    if readiness_next_phase_counts:
        for key in sorted(readiness_next_phase_counts):
            lines.append(f"- {key}: {readiness_next_phase_counts[key]}")
    else:
        lines.append("- no readiness notes were available")
    lines.append("")

    lines.extend(["## Readiness Execution Ready Counts", ""])
    if readiness_execution_ready_counts:
        for key in sorted(readiness_execution_ready_counts):
            lines.append(f"- {key}: {readiness_execution_ready_counts[key]}")
    else:
        lines.append("- no readiness execution-ready notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Decision Counts", ""])
    if phase_gate_decision_counts:
        for key in sorted(phase_gate_decision_counts):
            lines.append(f"- {key}: {phase_gate_decision_counts[key]}")
    else:
        lines.append("- no phase gate decision notes were available")
    lines.append("")

    lines.extend(["## Phase 2 Entry Allowed Counts", ""])
    if phase2_entry_allowed_counts:
        for key in sorted(phase2_entry_allowed_counts):
            lines.append(f"- {key}: {phase2_entry_allowed_counts[key]}")
    else:
        lines.append("- no phase2 entry notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Reason Counts", ""])
    if phase_gate_reason_counts:
        for key in sorted(phase_gate_reason_counts):
            lines.append(f"- {key}: {phase_gate_reason_counts[key]}")
    else:
        lines.append("- no phase gate reason notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Strict Validation Counts", ""])
    if phase_gate_strict_validation_passed_counts:
        for key in sorted(phase_gate_strict_validation_passed_counts):
            lines.append(f"- {key}: {phase_gate_strict_validation_passed_counts[key]}")
    else:
        lines.append("- no phase gate strict validation notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Strict Validation Issue Count Values", ""])
    if phase_gate_strict_validation_issue_count_values:
        for key in sorted(phase_gate_strict_validation_issue_count_values):
            lines.append(f"- {key}: {phase_gate_strict_validation_issue_count_values[key]}")
    else:
        lines.append("- no phase gate strict validation issue count notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Checked Files Values", ""])
    if phase_gate_checked_files_values:
        for key in sorted(phase_gate_checked_files_values):
            lines.append(f"- {key}: {phase_gate_checked_files_values[key]}")
    else:
        lines.append("- no phase gate checked files notes were available")
    lines.append("")

    lines.extend(
        [
            "## Recent Audit Timeline",
            "",
        ]
    )
    if recent:
        for item in recent:
            notes = item.get("notes", [])
            notes_text = ", ".join(str(x) for x in notes) if isinstance(notes, list) else ""
            lines.append(
                f"- {item.get('created_at')} | op={item.get('operation')} | status={item.get('status')} | notes={notes_text}"
            )
    else:
        lines.append("- no audit timeline entries available")
    lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
