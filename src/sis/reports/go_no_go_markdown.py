from __future__ import annotations

from pathlib import Path

from sis.models import GoNoGoReport
from sis.reports import go_no_go_markdown_navigation
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_sections,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


_reports_dir = go_no_go_markdown_navigation.reports_dir
_quick_navigation = go_no_go_markdown_navigation.quick_navigation
_related_reports = go_no_go_markdown_navigation.related_reports


def write_go_no_go_markdown(
    report: GoNoGoReport,
    out_path: Path,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    readiness_summary = normalize_readiness_summary(readiness_summary)
    execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    rows = "\n".join(
        f"| {item.criterion} | {item.result} | {item.evidence or ''} |" for item in report.criteria
    )
    blockers = "\n".join(f"- {item}" for item in report.blockers) or "- none"
    next_actions = "\n".join(f"- {item}" for item in report.next_actions) or "- none"
    venue_decision_rows = (
        "\n".join(
            f"| {item.venue} | {item.decision.value} | {item.main_blocker or ''} |"
            for item in report.venue_decisions
        )
        or "| none |  |  |"
    )
    quick_navigation = _quick_navigation(out_path, phase_gate_summary, readiness_summary)
    related_reports = _related_reports(
        out_path,
        phase_gate_summary,
        readiness_summary,
        execution_summary,
        execution_comparison_summary,
        execution_diagnostics_summary,
        execution_gap_history_summary,
        execution_state_comparison_summary,
        execution_snapshot_drift_summary,
        execution_drift_overview_summary,
    )
    lines = [
        "# Go/No-Go Report",
        "",
        "## Decision",
        "",
        f"`{report.decision.value}`",
        "",
        "## Summary",
        "",
        report.summary,
        "",
    ]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    if isinstance(audit_summary, dict) and any(audit_summary.values()):
        audit_summary_flat = audit_summary_fields(audit_summary, audit_summary)
        lines.extend(
            [
                "## Audit Summary",
                "",
                f"- overall_status: {audit_summary_flat.get('overall_status') or ''}",
                f"- latest_operation: {audit_summary_flat.get('latest_operation') or ''}",
                f"- bundle_history_snapshot_count: {audit_summary_flat.get('bundle_history_snapshot_count') or ''}",
                "",
            ]
        )
    if isinstance(phase_gate_summary, dict) and any(phase_gate_summary.values()):
        phase_gate_flat = phase_gate_flat_fields(phase_gate_summary)
        lines.extend(
            [
                "## Phase Gate Summary",
                "",
                f"- decision: {phase_gate_flat.get('phase_gate_decision') or ''}",
                f"- phase2_entry_allowed: {phase_gate_flat.get('phase2_entry_allowed')}",
                f"- phase_gate_reason: {phase_gate_flat.get('phase_gate_reason') or ''}",
                f"- strict_validation_passed: {phase_gate_flat.get('strict_validation_passed')}",
                (
                    "- phase_gate_strict_validation_issue_count: "
                    f"{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}"
                ),
                f"- phase_gate_checked_files: {phase_gate_flat.get('phase_gate_checked_files')}",
                "",
            ]
        )
    if isinstance(readiness_summary, dict) and any(readiness_summary.values()):
        readiness_flat = readiness_flat_fields(readiness_summary)
        lines.extend(
            [
                "## Readiness Summary",
                "",
                f"- next_phase_candidate: {readiness_flat.get('readiness_next_phase_candidate') or ''}",
                f"- execution_ready: {readiness_flat.get('readiness_execution_ready')}",
                f"- phase_gate_decision: {readiness_flat.get('phase_gate_decision') or ''}",
                f"- phase2_entry_allowed: {readiness_flat.get('phase2_entry_allowed')}",
                "",
            ]
        )
    if isinstance(execution_summary, dict) and any(execution_summary.values()):
        execution_summary_flat = execution_snapshot_flat_fields(execution_summary)
        lines.extend(
            [
                "## Execution Snapshot",
                "",
                f"- overall_status: {execution_summary_flat.get('execution_overall_status') or ''}",
                f"- venue_count: {execution_summary_flat.get('execution_venue_count')}",
                f"- report_path: {execution_summary_flat.get('execution_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_comparison_summary, dict) and any(
        execution_comparison_summary.values()
    ):
        execution_comparison_flat = execution_comparison_flat_fields(execution_comparison_summary)
        lines.extend(
            [
                "## Execution Venue Comparison",
                "",
                (
                    "- all_registries_present: "
                    f"{execution_comparison_flat.get('execution_comparison_all_registries_present')}"
                ),
                f"- report_path: {execution_comparison_flat.get('execution_comparison_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_diagnostics_summary, dict) and any(
        execution_diagnostics_summary.values()
    ):
        execution_diagnostics_flat = execution_diagnostics_flat_fields(
            execution_diagnostics_summary
        )
        lines.extend(
            [
                "## Execution Venue Diagnostics",
                "",
                f"- overall_status: {execution_diagnostics_flat.get('execution_diagnostics_status') or ''}",
                f"- balance_gap_detected: {execution_diagnostics_flat.get('execution_balance_gap_detected')}",
                f"- fills_gap_detected: {execution_diagnostics_flat.get('execution_fills_gap_detected')}",
                f"- report_path: {execution_diagnostics_flat.get('execution_diagnostics_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_gap_history_summary, dict) and any(
        execution_gap_history_summary.values()
    ):
        execution_gap_history_flat = execution_gap_history_flat_fields(
            execution_gap_history_summary
        )
        lines.extend(
            [
                "## Execution Gap History",
                "",
                f"- entry_count: {execution_gap_history_flat.get('execution_gap_history_entry_count')}",
                f"- latest_status: {execution_gap_history_flat.get('execution_gap_history_latest_status') or ''}",
                (
                    "- latest_execution_diagnostics_status: "
                    f"{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status') or ''}"
                ),
                f"- report_path: {execution_gap_history_flat.get('execution_gap_history_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_state_comparison_summary, dict) and any(
        execution_state_comparison_summary.values()
    ):
        execution_state_comparison_flat = execution_state_comparison_flat_fields(
            execution_state_comparison_summary
        )
        lines.extend(
            [
                "## Execution State Comparison History",
                "",
                f"- entry_count: {execution_state_comparison_flat.get('execution_state_comparison_entry_count')}",
                (
                    "- latest_status_match: "
                    f"{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}"
                ),
                (
                    "- mismatching_count: "
                    f"{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}"
                ),
                f"- report_path: {execution_state_comparison_flat.get('execution_state_comparison_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_snapshot_drift_summary, dict) and any(
        execution_snapshot_drift_summary.values()
    ):
        execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
            execution_snapshot_drift_summary
        )
        lines.extend(
            [
                "## Execution Snapshot Drift History",
                "",
                f"- entry_count: {execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}",
                (
                    "- latest_status_match: "
                    f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}"
                ),
                (
                    "- mismatching_snapshot_count: "
                    f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}"
                ),
                f"- report_path: {execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_drift_overview_summary, dict) and any(
        execution_drift_overview_summary.values()
    ):
        execution_drift_flat = execution_drift_overview_flat_fields(
            execution_drift_overview_summary
        )
        lines.extend(
            [
                "## Execution Drift Overview",
                "",
                f"- overall_status: {execution_drift_flat.get('execution_drift_overview_status') or ''}",
                (
                    "- diagnostics_alignment_match: "
                    f"{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}"
                ),
                (
                    "- state_comparison_mismatching_count: "
                    f"{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}"
                ),
                (
                    "- snapshot_drift_mismatching_snapshot_count: "
                    f"{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
                ),
                f"- report_path: {execution_drift_flat.get('execution_drift_overview_report_path') or ''}",
                "",
            ]
        )
    lines.extend(
        latest_execution_sections(
            [
                (
                    "## Audit Timeline Latest Execution",
                    timeline_latest_execution_summary,
                    timeline_latest_execution_comparison_summary,
                ),
                (
                    "## Audit Bundle History Latest Execution",
                    bundle_history_latest_execution_summary,
                    bundle_history_latest_execution_comparison_summary,
                ),
                (
                    "## Cycle History Latest Execution",
                    cycle_history_latest_execution_summary,
                    cycle_history_latest_execution_comparison_summary,
                ),
            ]
        )
    )
    lines.extend(
        [
            "## Criteria",
            "",
            "| Criterion | Result | Evidence |",
            "|---|---|---|",
            rows,
            "",
            "## Venue Decisions",
            "",
            "| Venue | Decision | Main Blocker |",
            "|---|---|---|",
            venue_decision_rows,
            "",
            "## Blockers",
            "",
            blockers,
            "",
            "## Next Actions",
            "",
            next_actions,
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")
