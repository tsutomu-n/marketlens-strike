from __future__ import annotations

from pathlib import Path

from sis.reports.operation_chain_notes import (
    latest_notes_with_prefix,
    note_counts,
    remediation_state,
    reports_dir,
    timeline_latest_note_summary,
)
from sis.reports.summary_normalizers import latest_execution_lineage_from_notes
from sis.reports.operations_timeline_markdown import render_operations_timeline_markdown
from sis.storage.jsonl_store import read_jsonl, write_json


def _quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("operations_timeline_report", summary.get("operations_timeline_report_path")),
        ("operations_dashboard_report", summary.get("operations_dashboard_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("operations_timeline_report", summary.get("operations_timeline_report_path")),
        ("operations_dashboard_report", summary.get("operations_dashboard_report_path")),
        ("ops_review_report", summary.get("ops_review_report_path")),
        ("operations_bundle_report", summary.get("operations_bundle_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("audit_bundle_report", summary.get("audit_bundle_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("paper_operations_runbook_report", summary.get("paper_operations_runbook_report_path")),
        ("phase_gate_review_report", summary.get("latest_phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_operations_timeline_report(
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
    recent = operations[-limit:]

    counts: dict[str, int] = {}
    for item in operations:
        operation = str(item.get("operation", "unknown"))
        counts[operation] = counts.get(operation, 0) + 1

    diagnostics_status_counts = note_counts(operations, "execution_diagnostics_status=")
    drift_overview_status_counts = note_counts(operations, "execution_drift_overview_status=")
    drift_overview_diagnostics_alignment_counts = note_counts(
        operations, "execution_drift_overview_diagnostics_alignment_match="
    )
    drift_overview_state_comparison_mismatching_count_values = note_counts(
        operations, "execution_drift_overview_state_comparison_mismatching_count="
    )
    drift_overview_snapshot_drift_mismatching_snapshot_count_values = note_counts(
        operations, "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
    )
    gap_history_status_counts = note_counts(operations, "execution_gap_history_latest_status=")
    gap_history_diagnostics_status_counts = note_counts(
        operations, "execution_gap_history_latest_diagnostics_status="
    )
    state_comparison_status_match_counts = note_counts(
        operations, "execution_state_comparison_latest_status_match="
    )
    state_comparison_mismatching_count_values = note_counts(
        operations, "execution_state_comparison_mismatching_count="
    )
    readiness_next_phase_counts = note_counts(operations, "readiness_next_phase=")
    latest = recent[-1] if recent else {}
    latest_execution_notes = latest_notes_with_prefix(operations, "execution_diagnostics_status=")
    latest_readiness_notes = latest_notes_with_prefix(operations, "readiness_next_phase=")
    latest_phase_gate_notes = latest_notes_with_prefix(operations, "phase_gate_decision=")
    phase_gate_decision_counts = note_counts(operations, "phase_gate_decision=")
    phase2_entry_allowed_counts = note_counts(operations, "phase2_entry_allowed=")
    phase_gate_reason_counts = note_counts(operations, "phase_gate_reason=")
    phase_gate_strict_validation_passed_counts = note_counts(
        operations, "phase_gate_strict_validation_passed="
    )
    phase_gate_strict_validation_issue_count_values = note_counts(
        operations, "phase_gate_strict_validation_issue_count="
    )
    phase_gate_checked_files_values = note_counts(operations, "phase_gate_checked_files=")
    latest_execution_lineage = latest_execution_lineage_from_notes(latest_execution_notes)
    latest_note_summary = timeline_latest_note_summary(
        execution_notes=latest_execution_notes,
        readiness_notes=latest_readiness_notes,
        phase_gate_notes=latest_phase_gate_notes,
    )
    remediation_summary = remediation_state(operations)
    reports_dir_value = reports_dir(operation_chain_path)

    summary = {
        "operation_count": len(operations),
        "recent_count": len(recent),
        "latest_operation": latest.get("operation") if latest else None,
        "latest_status": latest.get("status") if latest else None,
        **latest_execution_lineage,
        **latest_note_summary,
        "operation_counts": counts,
        **remediation_summary,
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
        "phase_gate_decision_counts": phase_gate_decision_counts,
        "phase2_entry_allowed_counts": phase2_entry_allowed_counts,
        "phase_gate_reason_counts": phase_gate_reason_counts,
        "phase_gate_strict_validation_passed_counts": phase_gate_strict_validation_passed_counts,
        "phase_gate_strict_validation_issue_count_values": phase_gate_strict_validation_issue_count_values,
        "phase_gate_checked_files_values": phase_gate_checked_files_values,
        "operations_timeline_report_path": str(out_path) if out_path is not None else None,
        "operations_dashboard_report_path": (
            str(reports_dir_value / "operations_dashboard.md") if reports_dir_value else None
        ),
        "ops_review_report_path": str(reports_dir_value / "ops_review_report.md")
        if reports_dir_value
        else None,
        "operations_bundle_report_path": (
            str(reports_dir_value / "operations_bundle_manifest.md") if reports_dir_value else None
        ),
        "audit_dashboard_report_path": str(reports_dir_value / "audit_dashboard.md")
        if reports_dir_value
        else None,
        "audit_bundle_report_path": (
            str(reports_dir_value / "audit_bundle_manifest.md") if reports_dir_value else None
        ),
        "current_state_index_report_path": str(reports_dir_value / "current_state_index.md")
        if reports_dir_value
        else None,
        "readiness_snapshot_report_path": str(reports_dir_value / "readiness_snapshot.md")
        if reports_dir_value
        else None,
        "paper_operations_runbook_report_path": (
            str(reports_dir_value / "paper_operations_runbook.md") if reports_dir_value else None
        ),
        "remediation_scoreboard_report_path": (
            str(reports_dir_value / "remediation_scoreboard.md") if reports_dir_value else None
        ),
    }
    quick_navigation = _quick_navigation(summary)
    related_reports = _related_reports(summary)
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports

    text = render_operations_timeline_markdown(summary=summary, recent=recent)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
