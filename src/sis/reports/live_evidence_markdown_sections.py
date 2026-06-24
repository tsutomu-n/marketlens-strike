from __future__ import annotations

from typing import Any

from sis.reports.live_evidence_sections import (
    latest_execution_lineage_flat_values,
    latest_execution_lineage_markdown_lines,
    quick_navigation_lines,
    related_report_lines,
    remediation_markdown_lines,
    restart_pointer_lines,
)
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


def summary_markdown_lines(data: Any) -> list[str]:
    phase_gate_flat = phase_gate_flat_fields(data.phase_gate_summary)
    readiness_flat = readiness_flat_fields(data.readiness_summary)
    latest_execution_flat = latest_execution_lineage_flat_values(data)
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        data.execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        data.execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        data.execution_drift_overview_summary
    )
    audit_summary_flat = audit_summary_fields(data.audit_summary, data.audit_summary)

    lines = [
        "# Live Evidence Detailed Report",
        "",
        "## Status",
        "",
        f"- run_status: `{data.status}`",
        f"- started_at_utc: `{data.started_at_utc}`",
        f"- finished_at_utc: `{data.finished_at_utc}`",
        f"- decision: `{data.decision}`",
        f"- log_path: `{data.log_path}`",
        f"- manifest_path: `{data.manifest_path}`",
        "",
    ]
    if data.audit_summary:
        lines.extend(
            [
                "## Audit Summary",
                "",
                f"- overall_status: `{audit_summary_flat.get('overall_status')}`",
                f"- latest_operation: `{audit_summary_flat.get('latest_operation')}`",
                (
                    "- bundle_history_snapshot_count: "
                    f"`{audit_summary_flat.get('bundle_history_snapshot_count')}`"
                ),
                "",
            ]
        )
    if data.phase_gate_summary:
        lines.extend(
            [
                "## Phase Gate Summary",
                "",
                f"- decision: `{phase_gate_flat.get('phase_gate_decision')}`",
                f"- phase2_entry_allowed: `{phase_gate_flat.get('phase2_entry_allowed')}`",
                f"- phase_gate_reason: `{phase_gate_flat.get('phase_gate_reason')}`",
                f"- strict_validation_passed: `{phase_gate_flat.get('strict_validation_passed')}`",
                (
                    "- phase_gate_strict_validation_issue_count: "
                    f"`{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}`"
                ),
                f"- phase_gate_checked_files: `{phase_gate_flat.get('phase_gate_checked_files')}`",
                "",
            ]
        )
    if data.readiness_summary:
        lines.extend(
            [
                "## Readiness Summary",
                "",
                (
                    "- next_phase_candidate: "
                    f"`{readiness_flat.get('readiness_next_phase_candidate')}`"
                ),
                f"- execution_ready: `{readiness_flat.get('readiness_execution_ready')}`",
                "",
            ]
        )
        if data.readiness_summary.get("timeline_latest_remediation_planner_status") is not None:
            lines.extend(["## Current Remediation Queue", ""])
            lines.extend(remediation_markdown_lines(data.readiness_summary))
            lines.append("")
        restart_lines = restart_pointer_lines(data.readiness_summary)
        if restart_lines:
            lines.extend(["## Restart Pointers", ""])
            lines.extend(restart_lines)
            lines.append("")
        navigation_lines = quick_navigation_lines(
            data.readiness_summary,
            data.phase_gate_summary,
        )
        if navigation_lines:
            lines.extend(["## Quick Navigation", ""])
            lines.extend(navigation_lines)
            lines.append("")
        report_lines = related_report_lines(
            data.readiness_summary,
            data.phase_gate_summary,
        )
        if report_lines:
            lines.extend(["## Related Reports", ""])
            lines.extend(report_lines)
            lines.append("")
    if any(
        (
            data.timeline_latest_execution_summary,
            data.bundle_history_latest_execution_summary,
            data.cycle_history_latest_execution_summary,
        )
    ):
        lines.extend(["## Latest Execution Lineage", ""])
        lines.extend(latest_execution_lineage_markdown_lines(latest_execution_flat))
        lines.append("")
    if data.execution_summary:
        lines.extend(
            [
                "## Execution Snapshot",
                "",
                f"- overall_status: `{execution_summary_flat.get('execution_overall_status')}`",
                f"- venue_count: `{execution_summary_flat.get('execution_venue_count')}`",
                f"- report_path: `{execution_summary_flat.get('execution_report_path')}`",
                "",
            ]
        )
    if data.execution_comparison_summary:
        lines.extend(
            [
                "## Execution Venue Comparison",
                "",
                (
                    "- all_registries_present: "
                    f"`{execution_comparison_flat.get('execution_comparison_all_registries_present')}`"
                ),
                (
                    "- report_path: "
                    f"`{execution_comparison_flat.get('execution_comparison_report_path')}`"
                ),
                "",
            ]
        )
    if data.execution_diagnostics_summary:
        lines.extend(
            [
                "## Execution Venue Diagnostics",
                "",
                (
                    "- overall_status: "
                    f"`{execution_diagnostics_flat.get('execution_diagnostics_status')}`"
                ),
                (
                    "- balance_gap_detected: "
                    f"`{execution_diagnostics_flat.get('execution_balance_gap_detected')}`"
                ),
                (
                    "- fills_gap_detected: "
                    f"`{execution_diagnostics_flat.get('execution_fills_gap_detected')}`"
                ),
                (
                    "- report_path: "
                    f"`{execution_diagnostics_flat.get('execution_diagnostics_report_path')}`"
                ),
                "",
            ]
        )
    if data.execution_gap_history_summary:
        lines.extend(
            [
                "## Execution Gap History",
                "",
                (
                    "- entry_count: "
                    f"`{execution_gap_history_flat.get('execution_gap_history_entry_count')}`"
                ),
                (
                    "- latest_status: "
                    f"`{execution_gap_history_flat.get('execution_gap_history_latest_status')}`"
                ),
                (
                    "- latest_execution_diagnostics_status: "
                    f"`{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status')}`"
                ),
                (
                    "- report_path: "
                    f"`{execution_gap_history_flat.get('execution_gap_history_report_path')}`"
                ),
                "",
            ]
        )
    if data.execution_state_comparison_summary:
        lines.extend(
            [
                "## Execution State Comparison History",
                "",
                (
                    "- entry_count: "
                    f"`{execution_state_comparison_flat.get('execution_state_comparison_entry_count')}`"
                ),
                (
                    "- latest_status_match: "
                    f"`{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}`"
                ),
                (
                    "- mismatching_count: "
                    f"`{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}`"
                ),
                (
                    "- report_path: "
                    f"`{execution_state_comparison_flat.get('execution_state_comparison_report_path')}`"
                ),
                "",
            ]
        )
    if data.execution_snapshot_drift_summary:
        lines.extend(
            [
                "## Execution Snapshot Drift History",
                "",
                (
                    "- entry_count: "
                    f"`{execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}`"
                ),
                (
                    "- latest_execution_state_comparison_status_match: "
                    f"`{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}`"
                ),
                (
                    "- mismatching_snapshot_count: "
                    f"`{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}`"
                ),
                (
                    "- report_path: "
                    f"`{execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path')}`"
                ),
                "",
            ]
        )
    if data.execution_drift_overview_summary:
        lines.extend(
            [
                "## Execution Drift Overview",
                "",
                f"- overall_status: `{execution_drift_flat.get('execution_drift_overview_status')}`",
                (
                    "- diagnostics_alignment_match: "
                    f"`{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}`"
                ),
                (
                    "- state_comparison_mismatching_count: "
                    f"`{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}`"
                ),
                (
                    "- snapshot_drift_mismatching_snapshot_count: "
                    f"`{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}`"
                ),
                "",
            ]
        )
    return lines
