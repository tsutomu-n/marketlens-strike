from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.reports import lifecycle_navigation
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    latest_execution_flat_sections,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


_quick_navigation = lifecycle_navigation.quick_navigation
_nested_report_path = lifecycle_navigation.nested_report_path
_related_reports = lifecycle_navigation.related_reports


def build_strategy_lifecycle_report(
    *,
    decision_summary_path: Path | None = None,
    weekly_review_path: Path | None = None,
    paper_last_run_path: Path | None = None,
    out_path: Path | None = None,
) -> str:
    lines = [
        "# Strategy Lifecycle Report",
        "",
    ]

    paper_payload = safe_read_json_dict(paper_last_run_path)
    quick_navigation = _quick_navigation(out_path, paper_payload)
    related_reports = _related_reports(out_path, paper_payload)
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")

    payload = safe_read_json_dict(decision_summary_path)
    if payload:
        lines.extend(
            [
                "## Decision Summary",
                "",
                f"- mode: {payload.get('mode')}",
                f"- signals_considered: {payload.get('signals_considered')}",
                f"- executed_count: {payload.get('executed_count')}",
                f"- blocked_count: {payload.get('blocked_count')}",
                "",
            ]
        )

    if weekly_review_path and weekly_review_path.exists():
        text = weekly_review_path.read_text(encoding="utf-8")
        lines.extend(
            [
                "## Weekly Review Reference",
                "",
                f"- source: {weekly_review_path}",
                "",
                "```md",
                text.strip(),
                "```",
                "",
            ]
        )

    payload = paper_payload
    if payload:
        audit = payload.get("audit")
        if isinstance(audit, dict):
            audit_summary_flat = audit_summary_fields(audit, audit)
            lines.extend(
                [
                    "## Paper Last Run Audit",
                    "",
                    f"- overall_status: {audit_summary_flat.get('overall_status')}",
                    f"- latest_operation: {audit_summary_flat.get('latest_operation')}",
                    f"- bundle_history_snapshot_count: {audit_summary_flat.get('bundle_history_snapshot_count')}",
                    "",
                ]
            )
        phase_gate = payload.get("phase_gate")
        if isinstance(phase_gate, dict):
            phase_gate = normalize_phase_gate_summary(phase_gate)
            phase_gate_flat = phase_gate_flat_fields(phase_gate)
            lines.extend(
                [
                    "## Paper Last Run Phase Gate",
                    "",
                    f"- decision: {phase_gate_flat.get('phase_gate_decision')}",
                    f"- phase2_entry_allowed: {phase_gate_flat.get('phase2_entry_allowed')}",
                    f"- phase_gate_reason: {phase_gate_flat.get('phase_gate_reason')}",
                    f"- strict_validation_passed: {phase_gate_flat.get('strict_validation_passed')}",
                    (
                        "- phase_gate_strict_validation_issue_count: "
                        f"{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}"
                    ),
                    f"- phase_gate_checked_files: {phase_gate_flat.get('phase_gate_checked_files')}",
                    "",
                ]
            )
        readiness = payload.get("readiness_summary")
        if isinstance(readiness, dict):
            readiness = normalize_readiness_summary(readiness)
            readiness_flat = readiness_flat_fields(readiness)
            lines.extend(
                [
                    "## Paper Last Run Readiness",
                    "",
                    (
                        "- next_phase_candidate: "
                        f"{readiness_flat.get('readiness_next_phase_candidate')}"
                    ),
                    f"- execution_ready: {readiness_flat.get('readiness_execution_ready')}",
                    "",
                ]
            )
        execution_summary = payload.get("execution_summary")
        if isinstance(execution_summary, dict):
            execution_summary = normalize_execution_snapshot_summary(execution_summary)
            execution_summary_flat = execution_snapshot_flat_fields(execution_summary)
            lines.extend(
                [
                    "## Paper Last Run Execution Snapshot",
                    "",
                    f"- overall_status: {execution_summary_flat.get('execution_overall_status')}",
                    f"- venue_count: {execution_summary_flat.get('execution_venue_count')}",
                    f"- report_path: {execution_summary_flat.get('execution_report_path')}",
                    "",
                ]
            )
        execution_comparison = payload.get("execution_comparison_summary")
        if isinstance(execution_comparison, dict):
            execution_comparison = normalize_execution_comparison_summary(execution_comparison)
            execution_comparison_flat = execution_comparison_flat_fields(execution_comparison)
            lines.extend(
                [
                    "## Paper Last Run Execution Venue Comparison",
                    "",
                    (
                        "- all_registries_present: "
                        f"{execution_comparison_flat.get('execution_comparison_all_registries_present')}"
                    ),
                    f"- report_path: {execution_comparison_flat.get('execution_comparison_report_path')}",
                    "",
                ]
            )
        execution_diagnostics = payload.get("execution_diagnostics_summary")
        if isinstance(execution_diagnostics, dict):
            execution_diagnostics = normalize_execution_diagnostics_summary(execution_diagnostics)
            execution_diagnostics_flat = execution_diagnostics_flat_fields(execution_diagnostics)
            lines.extend(
                [
                    "## Paper Last Run Execution Venue Diagnostics",
                    "",
                    f"- overall_status: {execution_diagnostics_flat.get('execution_diagnostics_status')}",
                    f"- balance_gap_detected: {execution_diagnostics_flat.get('execution_balance_gap_detected')}",
                    f"- fills_gap_detected: {execution_diagnostics_flat.get('execution_fills_gap_detected')}",
                    f"- report_path: {execution_diagnostics_flat.get('execution_diagnostics_report_path')}",
                    "",
                ]
            )
        execution_gap_history = payload.get("execution_gap_history_summary")
        if isinstance(execution_gap_history, dict):
            execution_gap_history = normalize_execution_gap_history_summary(execution_gap_history)
            execution_gap_history_flat = execution_gap_history_flat_fields(execution_gap_history)
            lines.extend(
                [
                    "## Paper Last Run Execution Gap History",
                    "",
                    f"- entry_count: {execution_gap_history_flat.get('execution_gap_history_entry_count')}",
                    f"- latest_status: {execution_gap_history_flat.get('execution_gap_history_latest_status')}",
                    (
                        "- latest_execution_diagnostics_status: "
                        f"{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status')}"
                    ),
                    f"- report_path: {execution_gap_history_flat.get('execution_gap_history_report_path')}",
                    "",
                ]
            )
        execution_state_comparison = payload.get("execution_state_comparison_summary")
        if isinstance(execution_state_comparison, dict):
            execution_state_comparison = normalize_execution_state_comparison_summary(
                execution_state_comparison
            )
            execution_state_comparison_flat = execution_state_comparison_flat_fields(
                execution_state_comparison
            )
            lines.extend(
                [
                    "## Paper Last Run Execution State Comparison History",
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
                    f"- report_path: {execution_state_comparison_flat.get('execution_state_comparison_report_path')}",
                    "",
                ]
            )
        execution_snapshot_drift = payload.get("execution_snapshot_drift_summary")
        if isinstance(execution_snapshot_drift, dict):
            execution_snapshot_drift = normalize_execution_snapshot_drift_summary(
                execution_snapshot_drift
            )
            execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
                execution_snapshot_drift
            )
            lines.extend(
                [
                    "## Paper Last Run Execution Snapshot Drift History",
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
                    f"- report_path: {execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path')}",
                    "",
                ]
            )
        execution_drift_overview = payload.get("execution_drift_overview_summary")
        if isinstance(execution_drift_overview, dict):
            execution_drift_overview = normalize_execution_drift_overview_summary(
                execution_drift_overview
            )
            execution_drift_flat = execution_drift_overview_flat_fields(execution_drift_overview)
            lines.extend(
                [
                    "## Paper Last Run Execution Drift Overview",
                    "",
                    f"- overall_status: {execution_drift_flat.get('execution_drift_overview_status')}",
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
                    f"- report_path: {execution_drift_flat.get('execution_drift_overview_report_path')}",
                    "",
                ]
            )
        lines.extend(
            latest_execution_flat_sections(
                [
                    (
                        "## Paper Last Run Audit Timeline Latest Execution",
                        payload.get("timeline_latest_execution_overall_status"),
                        payload.get("timeline_latest_execution_venue_count"),
                        payload.get("timeline_latest_execution_comparison_all_registries_present"),
                    ),
                    (
                        "## Paper Last Run Audit Bundle History Latest Execution",
                        payload.get("bundle_history_latest_execution_overall_status"),
                        payload.get("bundle_history_latest_execution_venue_count"),
                        payload.get(
                            "bundle_history_latest_execution_comparison_all_registries_present"
                        ),
                    ),
                    (
                        "## Paper Last Run Cycle History Latest Execution",
                        payload.get("cycle_history_latest_execution_overall_status"),
                        payload.get("cycle_history_latest_execution_venue_count"),
                        payload.get(
                            "cycle_history_latest_execution_comparison_all_registries_present"
                        ),
                    ),
                ]
            )
        )

    if len(lines) == 2:
        lines.extend(
            [
                "## No Inputs",
                "",
                "- no decision summary or weekly review artifacts were available",
                "",
            ]
        )

    report = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
    return report
