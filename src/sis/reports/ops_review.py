from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_flat_fields,
    audit_dashboard_flat_fields,
    normalize_execution_snapshot_summary,
    execution_snapshot_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_json, read_jsonl, write_json


def build_ops_review_report(
    *,
    operation_chain_path: Path | None = None,
    monitoring_snapshot_path: Path | None = None,
    daemon_dry_run_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations = list(read_jsonl(operation_chain_path)) if operation_chain_path and operation_chain_path.exists() else []
    monitoring = read_json(monitoring_snapshot_path) if monitoring_snapshot_path and monitoring_snapshot_path.exists() else {}
    daemon_dry_run = read_json(daemon_dry_run_path) if daemon_dry_run_path and daemon_dry_run_path.exists() else {}
    execution_snapshot = normalize_execution_snapshot_summary(
        read_json(execution_snapshot_summary_path)
        if execution_snapshot_summary_path and execution_snapshot_summary_path.exists()
        else {}
    )
    audit_dashboard = read_json(audit_dashboard_summary_path) if audit_dashboard_summary_path and audit_dashboard_summary_path.exists() else {}
    audit_bundle = read_json(audit_bundle_summary_path) if audit_bundle_summary_path and audit_bundle_summary_path.exists() else {}
    phase_gate = normalize_phase_gate_summary(
        read_json(phase_gate_summary_path) if phase_gate_summary_path and phase_gate_summary_path.exists() else {}
    )
    execution_drift_overview = normalize_execution_drift_overview_summary(
        read_json(execution_drift_overview_summary_path)
        if execution_drift_overview_summary_path and execution_drift_overview_summary_path.exists()
        else {}
    )
    readiness = normalize_readiness_summary(
        read_json(readiness_summary_path) if readiness_summary_path and readiness_summary_path.exists() else {}
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_snapshot)
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard)
    audit_bundle_fields = audit_bundle_flat_fields(audit_bundle)
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    readiness_fields = readiness_flat_fields(readiness)

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
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
        "execution_summary": execution_snapshot,
        "execution_drift_overview_summary": execution_drift_overview,
        **execution_snapshot_fields,
        **audit_dashboard_fields,
        **audit_bundle_fields,
        **phase_gate_fields,
        **execution_drift_fields,
        **readiness_fields,
        "status_counts": status_counts,
    }

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
        "",
        "## Strict Validation Preview",
        "",
        "## Status Counts",
        "",
    ]
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
