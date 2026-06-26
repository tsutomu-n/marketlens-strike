from __future__ import annotations

from collections.abc import Mapping

from sis.reports.summary_normalizers import (
    latest_execution_flat_lines,
    phase_gate_issue_preview_lines,
)


def artifact_summaries_section_lines(artifacts: Mapping[str, object]) -> list[str]:
    lines = [
        "## Artifact Summaries",
        "",
    ]
    for key, value in artifacts.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return lines


def audit_coverage_section_lines(summary: dict[str, object]) -> list[str]:
    return [
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
        (
            "- execution_comparison_all_registries_present: "
            f"{summary['execution_comparison_all_registries_present']}"
        ),
        f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
        f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
        f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
        f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}",
        f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}",
        (
            "- execution_gap_history_latest_diagnostics_status: "
            f"{summary['execution_gap_history_latest_diagnostics_status']}"
        ),
        (
            "- execution_state_comparison_entry_count: "
            f"{summary['execution_state_comparison_entry_count']}"
        ),
        (
            "- execution_state_comparison_latest_status_match: "
            f"{summary['execution_state_comparison_latest_status_match']}"
        ),
        (
            "- execution_state_comparison_mismatching_count: "
            f"{summary['execution_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_snapshot_drift_entry_count: "
            f"{summary['execution_snapshot_drift_entry_count']}"
        ),
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
        (
            "- timeline_latest_remediation_planner_status: "
            f"{summary['timeline_latest_remediation_planner_status']}"
        ),
        (
            "- timeline_latest_remediation_planner_next_best_command: "
            f"{summary['timeline_latest_remediation_planner_next_best_command']}"
        ),
        (
            "- timeline_latest_remediation_execution_plan_status: "
            f"{summary['timeline_latest_remediation_execution_plan_status']}"
        ),
        (
            "- timeline_latest_remediation_execution_plan_next_action_command: "
            f"{summary['timeline_latest_remediation_execution_plan_next_action_command']}"
        ),
        (
            "- timeline_latest_remediation_session_status: "
            f"{summary['timeline_latest_remediation_session_status']}"
        ),
        (
            "- timeline_latest_remediation_session_next_pending_command: "
            f"{summary['timeline_latest_remediation_session_next_pending_command']}"
        ),
        (
            "- timeline_latest_remediation_checkpoint_status: "
            f"{summary['timeline_latest_remediation_checkpoint_status']}"
        ),
        (
            "- timeline_latest_remediation_checkpoint_next_action_command: "
            f"{summary['timeline_latest_remediation_checkpoint_next_action_command']}"
        ),
        (
            "- timeline_latest_remediation_scoreboard_status: "
            f"{summary['timeline_latest_remediation_scoreboard_status']}"
        ),
        (
            "- timeline_latest_remediation_scoreboard_next_action_command: "
            f"{summary['timeline_latest_remediation_scoreboard_next_action_command']}"
        ),
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
        (
            "- phase_gate_strict_validation_issue_count: "
            f"{summary['phase_gate_strict_validation_issue_count']}"
        ),
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
        "",
    ]


def overall_section_lines(summary: dict[str, object]) -> list[str]:
    return [
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
    ]


def strict_validation_preview_section_lines(summary: dict[str, object]) -> list[str]:
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    lines = [
        "## Strict Validation Preview",
        "",
    ]
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.append("")
    return lines
