from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_history_flat_fields,
    audit_timeline_flat_fields,
    latest_execution_flat_lines,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    merged_remapped_latest_execution_lineage_fields,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import write_json


def _report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def _quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    phase_gate_summary_path = (
        Path(summary["phase_gate_summary_path"])
        if isinstance(summary.get("phase_gate_summary_path"), str)
        else None
    )
    items = (
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        (
            "current_state_index_report",
            _report_path_for_summary(phase_gate_summary_path, "current_state_index.md"),
        ),
        (
            "readiness_snapshot_report",
            _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md"),
        ),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "remediation_scoreboard_report",
            _report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md"),
        ),
        (
            "operations_audit_pack_report",
            _report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(summary: dict[str, object]) -> dict[str, str]:
    phase_gate_summary_path = (
        Path(summary["phase_gate_summary_path"])
        if isinstance(summary.get("phase_gate_summary_path"), str)
        else None
    )
    items = (
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        (
            "operations_dashboard_report",
            _report_path_for_summary(phase_gate_summary_path, "operations_dashboard.md"),
        ),
        (
            "current_state_index_report",
            _report_path_for_summary(phase_gate_summary_path, "current_state_index.md"),
        ),
        (
            "readiness_snapshot_report",
            _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md"),
        ),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "operations_bundle_report",
            _report_path_for_summary(phase_gate_summary_path, "operations_bundle_manifest.md"),
        ),
        (
            "audit_bundle_report",
            _report_path_for_summary(phase_gate_summary_path, "audit_bundle_manifest.md"),
        ),
        (
            "operations_audit_pack_report",
            _report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md"),
        ),
        (
            "paper_operations_runbook_report",
            _report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md"),
        ),
        (
            "remediation_scoreboard_report",
            _report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_audit_dashboard(
    *,
    bundle_manifest_path: Path | None = None,
    audit_pack_path: Path | None = None,
    audit_timeline_summary_path: Path | None = None,
    audit_bundle_history_summary_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    bundle = safe_read_json_dict(bundle_manifest_path)
    audit_pack = safe_read_json_dict(audit_pack_path)
    audit_timeline = safe_read_json_dict(audit_timeline_summary_path)
    audit_bundle_history = safe_read_json_dict(audit_bundle_history_summary_path)
    execution = normalized_summary(
        execution_snapshot_summary_path, normalize_execution_snapshot_summary
    )
    execution_comparison = normalized_summary(
        execution_venue_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    execution_diagnostics = normalized_summary(
        execution_venue_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    execution_state_comparison = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    readiness = normalized_summary(readiness_summary_path, normalize_readiness_summary)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(execution_snapshot_drift)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    audit_timeline_fields = audit_timeline_flat_fields(audit_timeline)
    audit_bundle_history_fields = audit_bundle_history_flat_fields(audit_bundle_history)
    audit_summary = audit_summary_fields(audit_pack, audit_bundle_history)
    readiness_fields = readiness_flat_fields(readiness)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    latest_execution_lineage = merged_remapped_latest_execution_lineage_fields(
        (audit_timeline, "timeline_latest"),
        (audit_bundle_history, "bundle_history_latest"),
    )
    operation_counts = audit_timeline.get("operation_counts")
    if not isinstance(operation_counts, dict):
        operation_counts = {}

    summary = {
        "overall_status": audit_pack.get("overall_status")
        or bundle.get("overall_status")
        or audit_timeline.get("latest_status"),
        "bundle_status": bundle.get("overall_status"),
        "audit_pack_status": audit_pack.get("overall_status"),
        **latest_execution_lineage,
        **audit_timeline_fields,
        "operations_snapshot_count": operation_counts.get("operations_snapshot"),
        "operations_audit_snapshot_count": operation_counts.get("operations_audit_snapshot"),
        "audit_bundle_snapshot_count": operation_counts.get("audit_bundle_snapshot"),
        "cycle_count": audit_pack.get("cycle_count") or bundle.get("cycle_count"),
        "completed_cycle_count": audit_pack.get("completed_cycle_count")
        or bundle.get("completed_cycle_count"),
        "audit_summary": audit_summary,
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
        **audit_bundle_history_fields,
        "execution_summary": execution,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **readiness_fields,
        **phase_gate_fields,
        "phase_gate_summary_path": str(phase_gate_summary_path)
        if phase_gate_summary_path
        else None,
        "audit_dashboard_report_path": str(out_path) if out_path is not None else None,
        "artifacts": {
            "bundle_manifest": str(bundle_manifest_path) if bundle_manifest_path else None,
            "audit_pack": str(audit_pack_path) if audit_pack_path else None,
            "audit_timeline_summary": str(audit_timeline_summary_path)
            if audit_timeline_summary_path
            else None,
            "audit_bundle_history_summary": str(audit_bundle_history_summary_path)
            if audit_bundle_history_summary_path
            else None,
            "execution_snapshot_summary": str(execution_snapshot_summary_path)
            if execution_snapshot_summary_path
            else None,
            "execution_venue_comparison_summary": (
                str(execution_venue_comparison_summary_path)
                if execution_venue_comparison_summary_path
                else None
            ),
            "execution_venue_diagnostics_summary": (
                str(execution_venue_diagnostics_summary_path)
                if execution_venue_diagnostics_summary_path
                else None
            ),
            "execution_gap_history_summary": (
                str(execution_gap_history_summary_path)
                if execution_gap_history_summary_path
                else None
            ),
            "execution_state_comparison_history_summary": (
                str(execution_state_comparison_history_summary_path)
                if execution_state_comparison_history_summary_path
                else None
            ),
            "execution_snapshot_drift_history_summary": (
                str(execution_snapshot_drift_history_summary_path)
                if execution_snapshot_drift_history_summary_path
                else None
            ),
            "execution_drift_overview_summary": (
                str(execution_drift_overview_summary_path)
                if execution_drift_overview_summary_path
                else None
            ),
            "readiness_summary": str(readiness_summary_path) if readiness_summary_path else None,
            "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
        },
    }
    quick_navigation = _quick_navigation(summary)
    related_reports = _related_reports(summary)
    artifacts = summary["artifacts"] if isinstance(summary.get("artifacts"), dict) else {}
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports

    lines = [
        "# Audit Dashboard",
        "",
        "## Overall",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- bundle_status: {summary['bundle_status']}",
        f"- audit_pack_status: {summary['audit_pack_status']}",
        f"- timeline_latest_operation: {summary['timeline_latest_operation']}",
        f"- timeline_latest_status: {summary['timeline_latest_status']}",
        *latest_execution_flat_lines(
            overall_status=summary.get("timeline_latest_execution_overall_status"),
            venue_count=summary.get("timeline_latest_execution_venue_count"),
            all_registries_present=summary.get(
                "timeline_latest_execution_comparison_all_registries_present"
            ),
            overall_status_label="timeline_latest_execution_overall_status",
            venue_count_label="timeline_latest_execution_venue_count",
            all_registries_present_label=(
                "timeline_latest_execution_comparison_all_registries_present"
            ),
        ),
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Audit Coverage",
            "",
            f"- audit_entry_count: {summary['audit_entry_count']}",
            f"- operations_snapshot_count: {summary['operations_snapshot_count']}",
            f"- operations_audit_snapshot_count: {summary['operations_audit_snapshot_count']}",
            f"- audit_bundle_snapshot_count: {summary['audit_bundle_snapshot_count']}",
            f"- cycle_count: {summary['cycle_count']}",
            f"- completed_cycle_count: {summary['completed_cycle_count']}",
            f"- bundle_history_snapshot_count: {summary['bundle_history_snapshot_count']}",
            f"- bundle_history_ok_count: {summary['bundle_history_ok_count']}",
            *latest_execution_flat_lines(
                overall_status=summary.get("bundle_history_latest_execution_overall_status"),
                venue_count=summary.get("bundle_history_latest_execution_venue_count"),
                all_registries_present=summary.get(
                    "bundle_history_latest_execution_comparison_all_registries_present"
                ),
                overall_status_label="bundle_history_latest_execution_overall_status",
                venue_count_label="bundle_history_latest_execution_venue_count",
                all_registries_present_label=(
                    "bundle_history_latest_execution_comparison_all_registries_present"
                ),
            ),
            f"- execution_overall_status: {summary['execution_overall_status']}",
            f"- execution_venue_count: {summary['execution_venue_count']}",
            f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}",
            f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
            f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
            f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
            f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}",
            f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}",
            f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}",
            f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}",
            (
                "- execution_state_comparison_latest_status_match: "
                f"{summary['execution_state_comparison_latest_status_match']}"
            ),
            (
                "- execution_state_comparison_mismatching_count: "
                f"{summary['execution_state_comparison_mismatching_count']}"
            ),
            f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}",
            (
                "- execution_snapshot_drift_latest_status_match: "
                f"{summary['execution_snapshot_drift_latest_status_match']}"
            ),
            (
                "- execution_snapshot_drift_mismatching_snapshot_count: "
                f"{summary['execution_snapshot_drift_mismatching_snapshot_count']}"
            ),
            f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}",
            (
                "- execution_drift_overview_diagnostics_alignment_match: "
                f"{summary['execution_drift_overview_diagnostics_alignment_match']}"
            ),
            (
                "- execution_drift_overview_state_comparison_mismatching_count: "
                f"{summary['execution_drift_overview_state_comparison_mismatching_count']}"
            ),
            (
                "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
                f"{summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
            ),
            f"- readiness_next_phase_candidate: {summary['readiness_next_phase_candidate']}",
            f"- readiness_execution_ready: {summary['readiness_execution_ready']}",
            f"- timeline_latest_remediation_planner_status: {summary['timeline_latest_remediation_planner_status']}",
            f"- timeline_latest_remediation_planner_next_best_command: {summary['timeline_latest_remediation_planner_next_best_command']}",
            f"- timeline_latest_remediation_execution_plan_status: {summary['timeline_latest_remediation_execution_plan_status']}",
            f"- timeline_latest_remediation_execution_plan_next_action_command: {summary['timeline_latest_remediation_execution_plan_next_action_command']}",
            f"- timeline_latest_remediation_session_status: {summary['timeline_latest_remediation_session_status']}",
            f"- timeline_latest_remediation_session_next_pending_command: {summary['timeline_latest_remediation_session_next_pending_command']}",
            f"- timeline_latest_remediation_checkpoint_status: {summary['timeline_latest_remediation_checkpoint_status']}",
            f"- timeline_latest_remediation_checkpoint_next_action_command: {summary['timeline_latest_remediation_checkpoint_next_action_command']}",
            f"- timeline_latest_remediation_scoreboard_status: {summary['timeline_latest_remediation_scoreboard_status']}",
            f"- timeline_latest_remediation_scoreboard_next_action_command: {summary['timeline_latest_remediation_scoreboard_next_action_command']}",
            f"- phase_gate_decision: {summary['phase_gate_decision']}",
            f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
            f"- phase_gate_reason: {summary['phase_gate_reason']}",
            f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
            f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
            f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
            f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
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
            "## Strict Validation Preview",
            "",
        ]
    )
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(
        [
            "",
            "## Artifact Summaries",
            "",
        ]
    )
    for key, value in artifacts.items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
