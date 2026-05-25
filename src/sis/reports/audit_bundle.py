from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_bundle_history_flat_fields,
    audit_dashboard_flat_fields,
    audit_timeline_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    latest_execution_flat_lines,
    merged_remapped_latest_execution_lineage_fields,
    normalize_execution_drift_overview_summary,
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
        ("audit_bundle_report", str(out_path) if out_path is not None else None),
        ("audit_dashboard_report", _report_path_for_summary(phase_gate_summary_path, "audit_dashboard.md")),
        ("operations_dashboard_report", _report_path_for_summary(phase_gate_summary_path, "operations_dashboard.md")),
        ("operations_audit_pack_report", _report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md")),
        ("current_state_index_report", _report_path_for_summary(phase_gate_summary_path, "current_state_index.md")),
        ("readiness_snapshot_report", _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md")),
        ("phase_gate_review_report", _report_path_for_summary(phase_gate_summary_path, "phase_gate_review.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(phase_gate_summary_path: Path | None, out_path: Path | None) -> dict[str, str]:
    items = (
        ("audit_bundle_report", str(out_path) if out_path is not None else None),
        ("audit_dashboard_report", _report_path_for_summary(phase_gate_summary_path, "audit_dashboard.md")),
        ("operations_dashboard_report", _report_path_for_summary(phase_gate_summary_path, "operations_dashboard.md")),
        ("operations_bundle_report", _report_path_for_summary(phase_gate_summary_path, "operations_bundle.md")),
        ("operations_audit_pack_report", _report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md")),
        ("current_state_index_report", _report_path_for_summary(phase_gate_summary_path, "current_state_index.md")),
        ("readiness_snapshot_report", _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md")),
        ("phase_gate_review_report", _report_path_for_summary(phase_gate_summary_path, "phase_gate_review.md")),
        ("paper_operations_runbook_report", _report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_audit_bundle_manifest(
    *,
    audit_dashboard_summary_path: Path | None = None,
    audit_timeline_summary_path: Path | None = None,
    audit_pack_path: Path | None = None,
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
    manifest_path: Path | None = None,
) -> str:
    audit_dashboard = safe_read_json_dict(audit_dashboard_summary_path)
    audit_timeline = safe_read_json_dict(audit_timeline_summary_path)
    audit_pack = safe_read_json_dict(audit_pack_path)
    audit_bundle_history = safe_read_json_dict(audit_bundle_history_summary_path)
    execution = safe_read_json_dict(execution_snapshot_summary_path)
    execution_comparison = safe_read_json_dict(execution_venue_comparison_summary_path)
    execution_diagnostics = safe_read_json_dict(execution_venue_diagnostics_summary_path)
    execution_gap_history = safe_read_json_dict(execution_gap_history_summary_path)
    execution_state_comparison = safe_read_json_dict(execution_state_comparison_history_summary_path)
    execution_snapshot_drift = safe_read_json_dict(execution_snapshot_drift_history_summary_path)
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
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard)
    audit_timeline_fields = audit_timeline_flat_fields(audit_timeline)
    audit_bundle_history_fields = audit_bundle_history_flat_fields(audit_bundle_history)
    latest_execution_lineage = merged_remapped_latest_execution_lineage_fields(
        (audit_timeline, "timeline_latest"),
        (audit_bundle_history, "bundle_history_latest"),
    )
    readiness_fields = readiness_flat_fields(readiness)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    remediation_fields = {
        key: value
        for key, value in audit_timeline_fields.items()
        if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
    }

    manifest = {
        "overall_status": audit_dashboard_fields.get("audit_overall_status") or audit_pack.get("overall_status") or audit_timeline.get("latest_status"),
        "audit_dashboard_status": audit_dashboard_fields.get("audit_overall_status"),
        "audit_pack_status": audit_pack.get("overall_status"),
        **latest_execution_lineage,
        **audit_timeline_fields,
        "cycle_count": audit_pack.get("cycle_count") or audit_dashboard.get("cycle_count"),
        "completed_cycle_count": audit_pack.get("completed_cycle_count") or audit_dashboard.get("completed_cycle_count"),
        **remediation_fields,
        **audit_bundle_history_fields,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **readiness_fields,
        **phase_gate_fields,
        "phase_gate_review_report_path": phase_gate_fields.get("phase_gate_review_report_path"),
        "audit_bundle_report_path": str(out_path) if out_path is not None else None,
        "artifacts": {
            "audit_dashboard_summary": str(audit_dashboard_summary_path) if audit_dashboard_summary_path else None,
            "audit_timeline_summary": str(audit_timeline_summary_path) if audit_timeline_summary_path else None,
            "operations_audit_pack": str(audit_pack_path) if audit_pack_path else None,
            "audit_bundle_history_summary": str(audit_bundle_history_summary_path) if audit_bundle_history_summary_path else None,
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
                str(execution_drift_overview_summary_path)
                if execution_drift_overview_summary_path
                else None
            ),
            "readiness_summary": str(readiness_summary_path) if readiness_summary_path else None,
            "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
        },
    }
    manifest["quick_navigation"] = _quick_navigation(phase_gate_summary_path, out_path)
    manifest["related_reports"] = _related_reports(phase_gate_summary_path, out_path)

    lines = [
        "# Audit Bundle Manifest",
        "",
        "## Status",
        "",
        f"- overall_status: {manifest['overall_status']}",
        f"- audit_dashboard_status: {manifest['audit_dashboard_status']}",
        f"- audit_pack_status: {manifest['audit_pack_status']}",
        f"- timeline_latest_operation: {manifest['timeline_latest_operation']}",
        f"- timeline_latest_status: {manifest['timeline_latest_status']}",
        *latest_execution_flat_lines(
            overall_status=manifest.get("timeline_latest_execution_overall_status"),
            venue_count=manifest.get("timeline_latest_execution_venue_count"),
            all_registries_present=manifest.get(
                "timeline_latest_execution_comparison_all_registries_present"
            ),
            overall_status_label="timeline_latest_execution_overall_status",
            venue_count_label="timeline_latest_execution_venue_count",
            all_registries_present_label=(
                "timeline_latest_execution_comparison_all_registries_present"
            ),
        ),
        f"- timeline_latest_execution_gap_history_status: {manifest['timeline_latest_execution_gap_history_status']}",
        (
            "- timeline_latest_execution_gap_history_diagnostics_status: "
            f"{manifest['timeline_latest_execution_gap_history_diagnostics_status']}"
        ),
        f"- timeline_latest_readiness_execution_ready: {manifest['timeline_latest_readiness_execution_ready']}",
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
        "## Quick Navigation",
        "",
    ]
    for key, value in manifest["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- audit_entry_count: {manifest['audit_entry_count']}",
            f"- cycle_count: {manifest['cycle_count']}",
            f"- completed_cycle_count: {manifest['completed_cycle_count']}",
            f"- bundle_history_snapshot_count: {manifest['bundle_history_snapshot_count']}",
            f"- bundle_history_ok_count: {manifest['bundle_history_ok_count']}",
            *latest_execution_flat_lines(
                overall_status=manifest.get("bundle_history_latest_execution_overall_status"),
                venue_count=manifest.get("bundle_history_latest_execution_venue_count"),
                all_registries_present=manifest.get(
                    "bundle_history_latest_execution_comparison_all_registries_present"
                ),
                overall_status_label="bundle_history_latest_execution_overall_status",
                venue_count_label="bundle_history_latest_execution_venue_count",
                all_registries_present_label=(
                    "bundle_history_latest_execution_comparison_all_registries_present"
                ),
            ),
            (
                "- bundle_history_latest_execution_gap_history_status: "
                f"{manifest['bundle_history_latest_execution_gap_history_status']}"
            ),
            (
                "- bundle_history_latest_execution_gap_history_diagnostics_status: "
                f"{manifest['bundle_history_latest_execution_gap_history_diagnostics_status']}"
            ),
            f"- bundle_history_latest_readiness_execution_ready: {manifest['bundle_history_latest_readiness_execution_ready']}",
            f"- execution_overall_status: {manifest['execution_overall_status']}",
            f"- execution_venue_count: {manifest['execution_venue_count']}",
            f"- execution_comparison_all_registries_present: {manifest['execution_comparison_all_registries_present']}",
            f"- execution_diagnostics_status: {manifest['execution_diagnostics_status']}",
            f"- execution_balance_gap_detected: {manifest['execution_balance_gap_detected']}",
            f"- execution_fills_gap_detected: {manifest['execution_fills_gap_detected']}",
            f"- execution_gap_history_entry_count: {manifest['execution_gap_history_entry_count']}",
            f"- execution_gap_history_latest_status: {manifest['execution_gap_history_latest_status']}",
            (
                "- execution_gap_history_latest_diagnostics_status: "
                f"{manifest['execution_gap_history_latest_diagnostics_status']}"
            ),
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
            f"- phase_gate_decision: {manifest['phase_gate_decision']}",
            f"- phase2_entry_allowed: {manifest['phase2_entry_allowed']}",
            f"- phase_gate_reason: {manifest['phase_gate_reason']}",
            f"- phase_gate_strict_validation_passed: {manifest['phase_gate_strict_validation_passed']}",
            f"- phase_gate_strict_validation_issue_count: {manifest['phase_gate_strict_validation_issue_count']}",
            f"- phase_gate_checked_files: {manifest['phase_gate_checked_files']}",
            f"- phase_gate_review_report_path: {manifest['phase_gate_review_report_path']}",
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
            "## Included Summaries",
            "",
        ]
    )
    for key, value in manifest["artifacts"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if manifest_path is not None:
        write_json(manifest_path, manifest)
    return text
