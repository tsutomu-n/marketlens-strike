from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    latest_execution_flat_lines,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    ops_review_flat_fields,
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


def _quick_navigation(phase_gate_summary_path: Path | None, out_path: Path | None) -> dict[str, str]:
    items = (
        ("operations_bundle_report", str(out_path) if out_path is not None else None),
        ("operations_dashboard_report", _report_path_for_summary(phase_gate_summary_path, "operations_dashboard.md")),
        ("current_state_index_report", _report_path_for_summary(phase_gate_summary_path, "current_state_index.md")),
        ("readiness_snapshot_report", _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md")),
        ("phase_gate_review_report", _report_path_for_summary(phase_gate_summary_path, "phase_gate_review.md")),
        ("paper_operations_runbook_report", _report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md")),
        ("remediation_scoreboard_report", _report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(phase_gate_summary_path: Path | None, out_path: Path | None) -> dict[str, str]:
    items = (
        ("operations_bundle_report", str(out_path) if out_path is not None else None),
        ("operations_dashboard_report", _report_path_for_summary(phase_gate_summary_path, "operations_dashboard.md")),
        ("audit_dashboard_report", _report_path_for_summary(phase_gate_summary_path, "audit_dashboard.md")),
        ("operations_audit_pack_report", _report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md")),
        ("ops_review_report", _report_path_for_summary(phase_gate_summary_path, "ops_review_report.md")),
        ("current_state_index_report", _report_path_for_summary(phase_gate_summary_path, "current_state_index.md")),
        ("readiness_snapshot_report", _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md")),
        ("phase_gate_review_report", _report_path_for_summary(phase_gate_summary_path, "phase_gate_review.md")),
        ("paper_operations_runbook_report", _report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md")),
        ("remediation_scoreboard_report", _report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_operations_bundle_manifest(
    *,
    monitoring_summary_path: Path | None = None,
    ops_review_summary_path: Path | None = None,
    dashboard_summary_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    runbook_summary_path: Path | None = None,
    paper_cycle_history_summary_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    out_path: Path | None = None,
    manifest_path: Path | None = None,
) -> str:
    monitoring = safe_read_json_dict(monitoring_summary_path)
    ops_review = safe_read_json_dict(ops_review_summary_path)
    dashboard = safe_read_json_dict(dashboard_summary_path)
    execution = normalized_summary(execution_snapshot_summary_path, normalize_execution_snapshot_summary)
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
    runbook = safe_read_json_dict(runbook_summary_path)
    cycle_history = safe_read_json_dict(paper_cycle_history_summary_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    ops_review_fields = ops_review_flat_fields(ops_review)
    readiness_fields = readiness_flat_fields(readiness)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    cycle_history_latest_execution_lineage = merged_remapped_latest_execution_lineage_fields(
        (cycle_history, "cycle_history_latest"),
    )
    remediation_fields = {
        key: value
        for key, value in dashboard.items()
        if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
    }

    manifest = {
        "overall_status": dashboard.get("overall_status") or monitoring.get("status"),
        "monitoring_status": monitoring.get("status"),
        "ops_latest_status": ops_review_fields.get("ops_latest_status"),
        "dashboard_status": dashboard.get("overall_status"),
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
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
        "runbook_monitoring_status": runbook.get("monitoring_status"),
        "cycle_count": cycle_history.get("cycle_count"),
        "completed_cycle_count": cycle_history.get("completed_count"),
        **cycle_history_latest_execution_lineage,
        **remediation_fields,
        **phase_gate_fields,
        "phase_gate_review_report_path": phase_gate_fields.get("phase_gate_review_report_path"),
        "operations_bundle_report_path": str(out_path) if out_path is not None else None,
        "artifacts": {
            "monitoring_summary": str(monitoring_summary_path) if monitoring_summary_path else None,
            "ops_review_summary": str(ops_review_summary_path) if ops_review_summary_path else None,
            "dashboard_summary": str(dashboard_summary_path) if dashboard_summary_path else None,
            "execution_snapshot_summary": str(execution_snapshot_summary_path) if execution_snapshot_summary_path else None,
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
                str(execution_gap_history_summary_path) if execution_gap_history_summary_path else None
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
                str(execution_drift_overview_summary_path) if execution_drift_overview_summary_path else None
            ),
            "readiness_summary": str(readiness_summary_path) if readiness_summary_path else None,
            "runbook_summary": str(runbook_summary_path) if runbook_summary_path else None,
            "paper_cycle_history_summary": str(paper_cycle_history_summary_path) if paper_cycle_history_summary_path else None,
            "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
        },
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
            "data/ops/execution_drift_overview_summary.json",
            "data/ops/readiness_snapshot.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
            "data/reports/operations_dashboard.md",
            "data/reports/audit_dashboard.md",
            "data/reports/operations_audit_pack.md",
            "data/reports/paper_operations_runbook.md",
        ],
    }
    manifest["quick_navigation"] = _quick_navigation(phase_gate_summary_path, out_path)
    manifest["related_reports"] = _related_reports(phase_gate_summary_path, out_path)

    lines = [
        "# Operations Bundle Manifest",
        "",
        "## Status",
        "",
        f"- overall_status: {manifest['overall_status']}",
        f"- monitoring_status: {manifest['monitoring_status']}",
        f"- ops_latest_status: {manifest['ops_latest_status']}",
        f"- dashboard_status: {manifest['dashboard_status']}",
        f"- execution_overall_status: {manifest['execution_overall_status']}",
        f"- execution_venue_count: {manifest['execution_venue_count']}",
        f"- execution_comparison_all_registries_present: {manifest['execution_comparison_all_registries_present']}",
        f"- execution_diagnostics_status: {manifest['execution_diagnostics_status']}",
        f"- execution_balance_gap_detected: {manifest['execution_balance_gap_detected']}",
        f"- execution_fills_gap_detected: {manifest['execution_fills_gap_detected']}",
        f"- execution_gap_history_entry_count: {manifest['execution_gap_history_entry_count']}",
        f"- execution_gap_history_latest_status: {manifest['execution_gap_history_latest_status']}",
        f"- execution_gap_history_latest_diagnostics_status: {manifest['execution_gap_history_latest_diagnostics_status']}",
        f"- execution_state_comparison_entry_count: {manifest['execution_state_comparison_entry_count']}",
        (
            "- execution_state_comparison_latest_status_match: "
            f"{manifest['execution_state_comparison_latest_status_match']}"
        ),
        (
            "- execution_state_comparison_mismatching_count: "
            f"{manifest['execution_state_comparison_mismatching_count']}"
        ),
        f"- execution_snapshot_drift_entry_count: {manifest['execution_snapshot_drift_entry_count']}",
        (
            "- execution_snapshot_drift_latest_status_match: "
            f"{manifest['execution_snapshot_drift_latest_status_match']}"
        ),
        (
            "- execution_snapshot_drift_mismatching_snapshot_count: "
            f"{manifest['execution_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- execution_drift_overview_status: {manifest['execution_drift_overview_status']}",
        (
            "- execution_drift_overview_diagnostics_alignment_match: "
            f"{manifest['execution_drift_overview_diagnostics_alignment_match']}"
        ),
        (
            "- execution_drift_overview_state_comparison_mismatching_count: "
            f"{manifest['execution_drift_overview_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
            f"{manifest['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- readiness_next_phase_candidate: {manifest['readiness_next_phase_candidate']}",
        f"- readiness_execution_ready: {manifest['readiness_execution_ready']}",
        f"- runbook_monitoring_status: {manifest['runbook_monitoring_status']}",
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in manifest["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
        "## Cycle Coverage",
        "",
        f"- cycle_count: {manifest['cycle_count']}",
        f"- completed_cycle_count: {manifest['completed_cycle_count']}",
        *latest_execution_flat_lines(
            overall_status=manifest.get("cycle_history_latest_execution_overall_status"),
            venue_count=manifest.get("cycle_history_latest_execution_venue_count"),
            all_registries_present=manifest.get(
                "cycle_history_latest_execution_comparison_all_registries_present"
            ),
            overall_status_label="cycle_history_latest_execution_overall_status",
            venue_count_label="cycle_history_latest_execution_venue_count",
            all_registries_present_label=(
                "cycle_history_latest_execution_comparison_all_registries_present"
            ),
        ),
        f"- timeline_latest_remediation_planner_status: {manifest.get('timeline_latest_remediation_planner_status')}",
        f"- timeline_latest_remediation_planner_next_best_command: {manifest.get('timeline_latest_remediation_planner_next_best_command')}",
        (
            "- timeline_latest_remediation_planner_feedback_priority_reason: "
            f"{manifest.get('timeline_latest_remediation_planner_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_execution_plan_status: {manifest.get('timeline_latest_remediation_execution_plan_status')}",
        f"- timeline_latest_remediation_execution_plan_next_action_command: {manifest.get('timeline_latest_remediation_execution_plan_next_action_command')}",
        (
            "- timeline_latest_remediation_execution_plan_feedback_priority_reason: "
            f"{manifest.get('timeline_latest_remediation_execution_plan_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_session_status: {manifest.get('timeline_latest_remediation_session_status')}",
        f"- timeline_latest_remediation_session_next_pending_command: {manifest.get('timeline_latest_remediation_session_next_pending_command')}",
        (
            "- timeline_latest_remediation_session_feedback_priority_reason: "
            f"{manifest.get('timeline_latest_remediation_session_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_checkpoint_status: {manifest.get('timeline_latest_remediation_checkpoint_status')}",
        f"- timeline_latest_remediation_checkpoint_next_action_command: {manifest.get('timeline_latest_remediation_checkpoint_next_action_command')}",
        (
            "- timeline_latest_remediation_checkpoint_feedback_priority_reason: "
            f"{manifest.get('timeline_latest_remediation_checkpoint_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_scoreboard_status: {manifest.get('timeline_latest_remediation_scoreboard_status')}",
        f"- timeline_latest_remediation_scoreboard_next_action_command: {manifest.get('timeline_latest_remediation_scoreboard_next_action_command')}",
        (
            "- timeline_latest_remediation_scoreboard_feedback_priority_reason: "
            f"{manifest.get('timeline_latest_remediation_scoreboard_feedback_priority_reason')}"
        ),
        "",
        "## Related Reports",
        "",
        ]
    )
    for key, value in manifest["related_reports"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
        "## Phase Gate",
        "",
        f"- phase_gate_decision: {manifest['phase_gate_decision']}",
        f"- phase2_entry_allowed: {manifest['phase2_entry_allowed']}",
        f"- phase_gate_reason: {manifest['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {manifest['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {manifest['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {manifest['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {manifest['phase_gate_review_report_path']}",
        "",
        "## Strict Validation Preview",
        "",
        ]
    )
    validation_issue_previews = phase_gate_issue_preview_lines(manifest)
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
    for key, value in manifest["artifacts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Recommended Read Order",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in manifest["recommended_read_order"])
    lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if manifest_path is not None:
        write_json(manifest_path, manifest)
    return text
