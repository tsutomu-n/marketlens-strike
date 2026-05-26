from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_history_flat_fields,
    audit_bundle_flat_fields,
    audit_dashboard_flat_fields,
    audit_timeline_flat_fields,
    latest_execution_lineage_flat_lines,
    normalize_execution_snapshot_summary,
    execution_snapshot_flat_fields,
    execution_drift_overview_flat_fields,
    merged_latest_execution_lineage_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_jsonl, write_json


def _report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def _quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("ops_review_report", summary.get("ops_review_report_path")),
        ("operations_dashboard_report", summary.get("operations_dashboard_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(summary: dict[str, object]) -> dict[str, str]:
    items = (
        ("ops_review_report", summary.get("ops_review_report_path")),
        ("operations_dashboard_report", summary.get("operations_dashboard_report_path")),
        ("audit_dashboard_report", summary.get("audit_dashboard_report_path")),
        ("operations_bundle_report", summary.get("operations_bundle_report_path")),
        ("audit_bundle_report", summary.get("audit_bundle_report_path")),
        ("current_state_index_report", summary.get("current_state_index_report_path")),
        ("readiness_snapshot_report", summary.get("readiness_snapshot_report_path")),
        ("paper_operations_runbook_report", summary.get("paper_operations_runbook_report_path")),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        ("remediation_scoreboard_report", summary.get("remediation_scoreboard_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_ops_review_report(
    *,
    operation_chain_path: Path | None = None,
    monitoring_snapshot_path: Path | None = None,
    daemon_dry_run_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations = (
        list(read_jsonl(operation_chain_path))
        if operation_chain_path and operation_chain_path.exists()
        else []
    )
    monitoring = safe_read_json_dict(monitoring_snapshot_path)
    daemon_dry_run = safe_read_json_dict(daemon_dry_run_path)
    execution_snapshot = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    audit_dashboard = safe_read_json_dict(audit_dashboard_summary_path)
    audit_bundle = safe_read_json_dict(audit_bundle_summary_path)
    operations_bundle = safe_read_json_dict(operations_bundle_manifest_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    readiness = normalized_summary(readiness_summary_path, normalize_readiness_summary)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_snapshot)
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard)
    audit_bundle_fields = audit_bundle_flat_fields(audit_bundle)
    audit_timeline_fields = audit_timeline_flat_fields(audit_dashboard)
    audit_bundle_history_fields = audit_bundle_history_flat_fields(audit_bundle)
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    latest_execution_lineage = merged_latest_execution_lineage_fields(
        audit_dashboard,
        audit_bundle,
        operations_bundle,
    )
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    readiness_fields = readiness_flat_fields(readiness)
    remediation_fields = {
        key: value
        for source in (audit_dashboard, operations_bundle)
        if isinstance(source, dict)
        for key, value in source.items()
        if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
    }

    latest = operations[-1] if operations else {}
    status_counts: dict[str, int] = {}
    for item in operations:
        status = str(item.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = {
        "operations_count": len(operations),
        "latest_operation": latest.get("operation"),
        "latest_status": latest.get("status"),
        "latest_scheduled_for": latest.get("scheduled_for"),
        "monitoring_status": monitoring.get("status"),
        "daemon_dry_run_status": daemon_dry_run.get("status"),
        "audit_summary": audit_summary,
        **latest_execution_lineage,
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
        "execution_summary": execution_snapshot,
        "execution_drift_overview_summary": execution_drift_overview,
        **execution_snapshot_fields,
        **audit_dashboard_fields,
        **audit_bundle_fields,
        **audit_timeline_fields,
        **audit_bundle_history_fields,
        **phase_gate_fields,
        **execution_drift_fields,
        **readiness_fields,
        **remediation_fields,
        "status_counts": status_counts,
        "ops_review_report_path": str(out_path) if out_path is not None else None,
        "operations_dashboard_report_path": _report_path_for_summary(
            phase_gate_summary_path,
            "operations_dashboard.md",
        ),
        "audit_dashboard_report_path": (
            _report_path_for_summary(audit_dashboard_summary_path, "audit_dashboard.md")
            if audit_dashboard_summary_path is not None
            else _report_path_for_summary(phase_gate_summary_path, "audit_dashboard.md")
        ),
        "operations_bundle_report_path": _report_path_for_summary(
            operations_bundle_manifest_path,
            "operations_bundle_manifest.md",
        ),
        "audit_bundle_report_path": _report_path_for_summary(
            audit_bundle_summary_path,
            "audit_bundle_manifest.md",
        ),
        "current_state_index_report_path": _report_path_for_summary(
            readiness_summary_path,
            "current_state_index.md",
        ),
        "readiness_snapshot_report_path": _report_path_for_summary(
            readiness_summary_path,
            "readiness_snapshot.md",
        ),
        "paper_operations_runbook_report_path": _report_path_for_summary(
            phase_gate_summary_path,
            "paper_operations_runbook.md",
        ),
        "remediation_scoreboard_report_path": _report_path_for_summary(
            phase_gate_summary_path,
            "remediation_scoreboard.md",
        ),
    }
    summary["quick_navigation"] = _quick_navigation(summary)
    summary["related_reports"] = _related_reports(summary)

    lines = [
        "# Ops Review Report",
        "",
        "## Operation Chain",
        "",
        f"- operations_count: {summary['operations_count']}",
        f"- latest_operation: {summary['latest_operation']}",
        f"- latest_status: {summary['latest_status']}",
        f"- latest_scheduled_for: {summary['latest_scheduled_for']}",
        "",
        "## Monitoring Snapshot",
        "",
        f"- monitoring_status: {summary['monitoring_status']}",
        f"- daemon_dry_run_status: {summary['daemon_dry_run_status']}",
        f"- execution_overall_status: {summary['execution_overall_status']}",
        f"- execution_venue_count: {summary['execution_venue_count']}",
        f"- audit_overall_status: {summary['audit_overall_status']}",
        f"- audit_latest_operation: {summary['audit_latest_operation']}",
        f"- audit_bundle_history_snapshot_count: {summary['audit_bundle_history_snapshot_count']}",
        *latest_execution_lineage_flat_lines(summary),
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
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
        f"- timeline_latest_remediation_planner_status: {summary.get('timeline_latest_remediation_planner_status')}",
        f"- timeline_latest_remediation_planner_next_best_command: {summary.get('timeline_latest_remediation_planner_next_best_command')}",
        (
            "- timeline_latest_remediation_planner_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_planner_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_execution_plan_status: {summary.get('timeline_latest_remediation_execution_plan_status')}",
        f"- timeline_latest_remediation_execution_plan_next_action_command: {summary.get('timeline_latest_remediation_execution_plan_next_action_command')}",
        (
            "- timeline_latest_remediation_execution_plan_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_execution_plan_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_session_status: {summary.get('timeline_latest_remediation_session_status')}",
        f"- timeline_latest_remediation_session_next_pending_command: {summary.get('timeline_latest_remediation_session_next_pending_command')}",
        (
            "- timeline_latest_remediation_session_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_session_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_checkpoint_status: {summary.get('timeline_latest_remediation_checkpoint_status')}",
        f"- timeline_latest_remediation_checkpoint_next_action_command: {summary.get('timeline_latest_remediation_checkpoint_next_action_command')}",
        (
            "- timeline_latest_remediation_checkpoint_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_checkpoint_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_scoreboard_status: {summary.get('timeline_latest_remediation_scoreboard_status')}",
        f"- timeline_latest_remediation_scoreboard_next_action_command: {summary.get('timeline_latest_remediation_scoreboard_next_action_command')}",
        (
            "- timeline_latest_remediation_scoreboard_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_scoreboard_feedback_priority_reason')}"
        ),
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in summary["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Related Reports",
            "",
        ]
    )
    for key, value in summary["related_reports"].items():
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
    lines.extend(["", "## Status Counts", ""])
    if status_counts:
        for key in sorted(status_counts):
            lines.append(f"- {key}: {status_counts[key]}")
    else:
        lines.append("- no operation manifests were available")
    lines.append("")

    if latest:
        lines.extend(
            [
                "## Latest Operation Notes",
                "",
                f"- command: {latest.get('command')}",
                f"- artifacts: {', '.join(latest.get('artifacts', []))}",
                f"- notes: {', '.join(latest.get('notes', []))}",
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
