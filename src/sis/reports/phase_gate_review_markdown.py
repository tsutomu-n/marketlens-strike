from __future__ import annotations

from typing import Any

from sis.reports import (
    phase_gate_review_markdown_remediation,
    phase_gate_review_markdown_tables,
    phase_gate_review_markdown_values,
)
from sis.reports.summary_normalizers import latest_execution_lineage_flat_lines

_classification_counts = phase_gate_review_markdown_values.classification_counts
_as_str_list = phase_gate_review_markdown_values.as_str_list
_as_dict_list = phase_gate_review_markdown_values.as_dict_list
_as_mapping = phase_gate_review_markdown_values.as_mapping
_as_str_dict = phase_gate_review_markdown_values.as_str_dict
_as_list_mapping = phase_gate_review_markdown_values.as_list_mapping
_diagnostics_table_lines = phase_gate_review_markdown_tables.diagnostics_table_lines
_execution_drift_classification_lines = (
    phase_gate_review_markdown_tables.execution_drift_classification_lines
)
_remediation_section_lines = phase_gate_review_markdown_remediation.remediation_section_lines
_venue_decision_lines = phase_gate_review_markdown_tables.venue_decision_lines


def render_phase_gate_review_markdown(summary: dict[str, Any]) -> str:
    quick_navigation = _as_str_dict(summary.get("quick_navigation"))
    related_reports = _as_str_dict(summary.get("related_reports"))
    venue_decisions = _as_dict_list(summary.get("venue_decisions"))
    next_actions = _as_str_list(summary.get("next_actions"))
    recommended_read_order_items = _as_str_list(summary.get("recommended_read_order"))
    diagnostics = _as_dict_list(summary.get("diagnostics"))
    required_artifact_paths = _as_mapping(summary.get("required_artifact_paths"))
    missing_required_artifact_paths = _as_str_list(summary.get("missing_required_artifact_paths"))
    artifact_recovery_commands = _as_list_mapping(summary.get("artifact_recovery_commands"))
    remediation_order = _as_dict_list(summary.get("remediation_order"))
    remediation_success_criteria = _as_list_mapping(summary.get("remediation_success_criteria"))
    remediation_preflight_commands = _as_list_mapping(summary.get("remediation_preflight_commands"))
    remediation_postcheck_commands = _as_list_mapping(summary.get("remediation_postcheck_commands"))
    remediation_preflight_expected_outputs = _as_list_mapping(
        summary.get("remediation_preflight_expected_outputs")
    )
    remediation_execute_expected_outputs = _as_list_mapping(
        summary.get("remediation_execute_expected_outputs")
    )
    remediation_postcheck_pass_signals = _as_list_mapping(
        summary.get("remediation_postcheck_pass_signals")
    )
    remediation_signal_snapshots_before = _as_mapping(
        summary.get("remediation_signal_snapshots_before")
    )
    remediation_signal_snapshots_target = _as_mapping(
        summary.get("remediation_signal_snapshots_target")
    )
    remediation_signal_snapshot_diffs = _as_mapping(
        summary.get("remediation_signal_snapshot_diffs")
    )
    remediation_recommendations = _as_mapping(summary.get("remediation_recommendations"))

    lines = [
        "# Phase Gate Review",
        "",
        "## Executive Summary",
        "",
        f"- current_phase: {summary['current_phase']}",
        f"- decision: {summary['decision']}",
        f"- individual_stock_decision: {summary['individual_stock_decision']}",
        f"- index_only_decision: {summary['index_only_decision']}",
        f"- strict_validation_passed: {summary['strict_validation_passed']}",
        f"- strict_validation_issue_count: {summary['strict_validation_issue_count']}",
        f"- latest_manifest_status: {summary['latest_manifest_status']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase2_entry_reason: {summary['phase2_entry_reason']}",
        f"- read_only_collector_gate_passed: {summary['read_only_collector_gate_passed']}",
        f"- read_only_collector_blockers: {summary['read_only_collector_blockers'] or 'none'}",
        f"- latest_gtrade_backend_manifest_path: {summary['latest_gtrade_backend_manifest_path']}",
        f"- latest_ostium_constraint_path: {summary['latest_ostium_constraint_path']}",
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
        (
            "- execution_drift_p2_blocker_count: "
            f"{_classification_counts(summary).get('P2_BLOCKER')}"
        ),
        (
            "- execution_drift_live_readiness_blocker_count: "
            f"{_classification_counts(summary).get('LIVE_READINESS_BLOCKER')}"
        ),
        *latest_execution_lineage_flat_lines(summary),
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in related_reports.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Latest Artifacts",
            "",
            f"- latest_manifest_path: {summary['latest_manifest_path']}",
            f"- latest_evidence_card_path: {summary['latest_evidence_card_path']}",
            f"- latest_execution_snapshot_summary_path: {summary['latest_execution_snapshot_summary_path']}",
            f"- latest_execution_venue_comparison_summary_path: {summary['latest_execution_venue_comparison_summary_path']}",
            f"- latest_execution_venue_diagnostics_summary_path: {summary['latest_execution_venue_diagnostics_summary_path']}",
            f"- latest_execution_gap_history_summary_path: {summary['latest_execution_gap_history_summary_path']}",
            f"- latest_execution_state_comparison_history_summary_path: {summary['latest_execution_state_comparison_history_summary_path']}",
            f"- latest_execution_snapshot_drift_history_summary_path: {summary['latest_execution_snapshot_drift_history_summary_path']}",
            f"- latest_execution_drift_overview_summary_path: {summary['latest_execution_drift_overview_summary_path']}",
            "",
            "## Required Artifacts",
            "",
            "",
            "## Strict Validation",
            "",
            f"- checked_files: {summary['checked_files']}",
        ]
    )
    lines.extend(f"- {name}: {value}" for name, value in required_artifact_paths.items())
    if missing_required_artifact_paths:
        lines.append("- missing_required_artifact_paths:")
        lines.extend(f"  - {name}" for name in missing_required_artifact_paths)
    else:
        lines.append("- missing_required_artifact_paths: none")
    lines.extend(["", "## Recovery Commands", ""])
    if artifact_recovery_commands:
        for name, commands in artifact_recovery_commands.items():
            lines.append(f"- {name}:")
            lines.extend(f"  - `{command}`" for command in commands)
    else:
        lines.append("- recovery_commands: none")
    lines.extend(
        _remediation_section_lines(
            remediation_order=remediation_order,
            remediation_success_criteria=remediation_success_criteria,
            remediation_preflight_commands=remediation_preflight_commands,
            remediation_postcheck_commands=remediation_postcheck_commands,
            remediation_preflight_expected_outputs=remediation_preflight_expected_outputs,
            remediation_execute_expected_outputs=remediation_execute_expected_outputs,
            remediation_postcheck_pass_signals=remediation_postcheck_pass_signals,
            remediation_signal_snapshots_before=remediation_signal_snapshots_before,
            remediation_signal_snapshots_target=remediation_signal_snapshots_target,
            remediation_signal_snapshot_diffs=remediation_signal_snapshot_diffs,
            remediation_recommendations=remediation_recommendations,
        )
    )
    strict_validation_issues = _as_dict_list(summary.get("phase_gate_strict_validation_issues"))
    if strict_validation_issues:
        lines.append("")
        lines.append("| path | message |")
        lines.append("| --- | --- |")
        for issue in strict_validation_issues:
            path = issue.get("path", "")
            message = str(issue.get("message", "")).replace("|", "/")
            lines.append(f"| {path} | {message} |")
    else:
        lines.extend(["", "- issues: none"])

    lines.extend(["", "## Diagnostics", ""])
    lines.extend(_diagnostics_table_lines(diagnostics))

    lines.extend(["", "## Venue Decisions", ""])
    lines.extend(_venue_decision_lines(venue_decisions))

    lines.extend(["", "## Execution Snapshot", ""])
    lines.append(f"- execution_overall_status: {summary['execution_overall_status']}")
    lines.append(f"- execution_venue_count: {summary['execution_venue_count']}")
    lines.append(
        f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}"
    )
    lines.append(f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}")
    lines.append(f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}")
    lines.append(f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}")
    lines.append(
        f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}"
    )
    lines.append(
        f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}"
    )
    lines.append(
        f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}"
    )
    lines.append(
        f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}"
    )
    lines.append(
        f"- execution_state_comparison_latest_status_match: {summary['execution_state_comparison_latest_status_match']}"
    )
    lines.append(
        f"- execution_state_comparison_mismatching_count: {summary['execution_state_comparison_mismatching_count']}"
    )
    lines.append(
        f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}"
    )
    lines.append(
        f"- execution_snapshot_drift_latest_status_match: {summary['execution_snapshot_drift_latest_status_match']}"
    )
    lines.append(
        f"- execution_snapshot_drift_mismatching_snapshot_count: {summary['execution_snapshot_drift_mismatching_snapshot_count']}"
    )
    lines.append(f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}")
    lines.append(
        f"- execution_drift_overview_diagnostics_alignment_match: {summary['execution_drift_overview_diagnostics_alignment_match']}"
    )
    lines.append(
        f"- execution_drift_overview_state_comparison_mismatching_count: {summary['execution_drift_overview_state_comparison_mismatching_count']}"
    )
    lines.append(
        f"- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: {summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
    )
    lines.append(
        f"- latest_execution_snapshot_summary_path: {summary['latest_execution_snapshot_summary_path']}"
    )
    lines.append(
        f"- latest_execution_venue_comparison_summary_path: {summary['latest_execution_venue_comparison_summary_path']}"
    )
    lines.append(
        f"- latest_execution_venue_diagnostics_summary_path: {summary['latest_execution_venue_diagnostics_summary_path']}"
    )
    lines.append(
        f"- latest_execution_gap_history_summary_path: {summary['latest_execution_gap_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_state_comparison_history_summary_path: {summary['latest_execution_state_comparison_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_snapshot_drift_history_summary_path: {summary['latest_execution_snapshot_drift_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_drift_overview_summary_path: {summary['latest_execution_drift_overview_summary_path']}"
    )

    lines.extend(["", "## Execution Drift Classification", ""])
    classifications = _as_dict_list(summary.get("execution_drift_classifications"))
    lines.extend(_execution_drift_classification_lines(classifications))

    lines.extend(["", "## Next Actions", ""])
    if next_actions:
        lines.extend(f"- {item}" for item in next_actions)
    else:
        lines.extend(
            [
                "- recollect live evidence during the recommended window",
                "- rerun diagnose-quotes for SP500 / XYZ100 / NVDA / AAPL / MSFT",
                "- rerun validate-artifacts --strict",
                "- rerun check-go-no-go and build-evidence-card",
            ]
        )
    if remediation_order:
        lines.extend(
            [
                "- execute the commands in `Remediation Order` from lower priority number to higher",
            ]
        )

    lines.extend(["", "## Stop Conditions", ""])
    lines.extend(
        [
            "- If `missing_required_artifact_paths` is not empty, stop and regenerate the missing manifest or execution artifacts before continuing.",
            "- If `strict_validation_issue_count` is not `0`, stop and clear strict validation issues before considering Phase 2.",
            "- If `diagnostics_all_available` is not `True`, stop and recollect quote diagnostics for SP500 / XYZ100 / NVDA / AAPL / MSFT.",
            "- If `execution_drift_p2_blocker_count` is greater than `0`, stop before considering Phase 2.",
            "- If `execution_drift_live_readiness_blocker_count` is greater than `0`, stop before live execution readiness; do not treat it as a read-only Phase 2 blocker.",
            "- If `read_only_collector_gate_passed` is not `True`, stop and refresh Trade[XYZ] read-only artifacts with `collect-trade-xyz-quotes --write-summary --write-report` before considering Bot preview work.",
        ]
    )

    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in recommended_read_order_items)
    return "\n".join(lines) + "\n"
