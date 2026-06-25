from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports import paper_operations_runbook_paths
from sis.reports.paper_operations_runbook_remediation import (
    build_paper_operations_runbook_remediation_context,
)
from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    latest_execution_lineage_flat_lines,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    latest_execution_lineage_fields_from_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import write_json

_report_path_for_summary = paper_operations_runbook_paths.report_path_for_summary
_related_reports = paper_operations_runbook_paths.related_reports
_quick_navigation = paper_operations_runbook_paths.quick_navigation


def build_paper_operations_runbook(
    *,
    scheduled_run_path: Path | None = None,
    daemon_manifest_path: Path | None = None,
    monitoring_snapshot_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    ops_dashboard_summary_path: Path | None = None,
    remediation_planner_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    prior_summary = safe_read_json_dict(summary_path)
    scheduled_run = safe_read_json_dict(scheduled_run_path)
    daemon_manifest = safe_read_json_dict(daemon_manifest_path)
    monitoring = safe_read_json_dict(monitoring_snapshot_path)
    execution = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
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
    dashboard = safe_read_json_dict(ops_dashboard_summary_path)
    latest_execution_lineage = latest_execution_lineage_fields_from_summary(dashboard)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(execution_snapshot_drift)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    readiness_fields = readiness_flat_fields(readiness)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)

    summary = {
        "scheduled_run_type": scheduled_run.get("run_type"),
        "scheduled_for": scheduled_run.get("scheduled_for"),
        "scheduled_command": scheduled_run.get("command"),
        "scheduled_run_path": str(scheduled_run_path) if scheduled_run_path is not None else None,
        "daemon_manifest_path": str(daemon_manifest_path)
        if daemon_manifest_path is not None
        else None,
        "monitoring_snapshot_path": str(monitoring_snapshot_path)
        if monitoring_snapshot_path is not None
        else None,
        "execution_snapshot_summary_path": (
            str(execution_snapshot_summary_path)
            if execution_snapshot_summary_path is not None
            else None
        ),
        "execution_venue_comparison_summary_path": (
            str(execution_venue_comparison_summary_path)
            if execution_venue_comparison_summary_path is not None
            else None
        ),
        "execution_venue_diagnostics_summary_path": (
            str(execution_venue_diagnostics_summary_path)
            if execution_venue_diagnostics_summary_path is not None
            else None
        ),
        "execution_gap_history_summary_path": (
            str(execution_gap_history_summary_path)
            if execution_gap_history_summary_path is not None
            else None
        ),
        "execution_state_comparison_history_summary_path": (
            str(execution_state_comparison_history_summary_path)
            if execution_state_comparison_history_summary_path is not None
            else None
        ),
        "execution_snapshot_drift_history_summary_path": (
            str(execution_snapshot_drift_history_summary_path)
            if execution_snapshot_drift_history_summary_path is not None
            else None
        ),
        "execution_drift_overview_summary_path": (
            str(execution_drift_overview_summary_path)
            if execution_drift_overview_summary_path is not None
            else None
        ),
        "readiness_summary_path": str(readiness_summary_path)
        if readiness_summary_path is not None
        else None,
        "phase_gate_summary_path": str(phase_gate_summary_path)
        if phase_gate_summary_path is not None
        else None,
        "ops_dashboard_summary_path": str(ops_dashboard_summary_path)
        if ops_dashboard_summary_path is not None
        else None,
        "daemon_mode": daemon_manifest.get("mode"),
        "monitoring_status": monitoring.get("status"),
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
        "execution_summary": execution,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        **latest_execution_lineage,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **readiness_fields,
        **phase_gate_fields,
        **{
            key: value
            for key, value in dashboard.items()
            if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
        },
        "dashboard_status": dashboard.get("overall_status"),
    }
    required_artifact_paths = _required_artifact_paths(summary)
    missing_required_artifact_paths = [
        key for key, value in required_artifact_paths.items() if not value
    ]
    artifact_recovery_commands = _artifact_recovery_commands(missing_required_artifact_paths)
    remediation_order = _remediation_order(
        summary,
        missing_required_artifact_paths,
        artifact_recovery_commands,
    )
    remediation_success_criteria = {
        item["reason"]: _remediation_success_criteria(str(item["reason"]))
        for item in remediation_order
    }
    remediation_preflight_commands = {
        item["reason"]: _remediation_preflight_commands(str(item["reason"]))
        for item in remediation_order
    }
    remediation_postcheck_commands = {
        item["reason"]: _remediation_postcheck_commands(str(item["reason"]))
        for item in remediation_order
    }
    remediation_preflight_expected_outputs = {
        item["reason"]: _remediation_preflight_expected_outputs(str(item["reason"]))
        for item in remediation_order
    }
    remediation_execute_expected_outputs = {
        item["reason"]: _remediation_execute_expected_outputs(str(item["reason"]))
        for item in remediation_order
    }
    remediation_postcheck_pass_signals = {
        item["reason"]: _remediation_postcheck_pass_signals(str(item["reason"]))
        for item in remediation_order
    }
    remediation_signal_snapshots_before = {
        item["reason"]: _remediation_signal_snapshot_before(str(item["reason"]), summary)
        for item in remediation_order
    }
    remediation_signal_snapshots_target = {
        item["reason"]: _remediation_signal_snapshot_target(str(item["reason"]))
        for item in remediation_order
    }
    previous_signal_snapshots_value = prior_summary.get("remediation_signal_snapshots_before")
    previous_signal_snapshots = (
        cast(dict[str, Any], previous_signal_snapshots_value)
        if isinstance(previous_signal_snapshots_value, dict)
        else {}
    )
    remediation_signal_snapshot_diffs = {
        item["reason"]: compare_signal_snapshots(
            previous_signal_snapshots.get(str(item["reason"])),
            remediation_signal_snapshots_before.get(str(item["reason"])),
            remediation_signal_snapshots_target.get(str(item["reason"])),
        )
        for item in remediation_order
    }
    previous_recommendations_value = prior_summary.get("remediation_recommendations")
    previous_recommendations = (
        cast(dict[str, Any], previous_recommendations_value)
        if isinstance(previous_recommendations_value, dict)
        else {}
    )
    current_planner_summary = safe_read_json_dict(remediation_planner_summary_path)
    current_evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    current_planner_entries_value = current_planner_summary.get("entries")
    current_planner_entries = (
        cast(list[object], current_planner_entries_value)
        if isinstance(current_planner_entries_value, list)
        else []
    )
    current_provenance_hints = {
        str(cast(dict[str, Any], item).get("reason")): cast(dict[str, Any], item)
        for item in current_planner_entries
        if isinstance(item, dict)
        and cast(dict[str, Any], item).get("source") == "paper_operations_runbook"
        and cast(dict[str, Any], item).get("reason")
    }
    current_signal_provenance_hints = signal_observed_sources_by_reason(
        current_evaluator_summary,
        source="paper_operations_runbook",
    )
    remediation_recommendations = {
        str(item["reason"]): recommend_remediation_actions(
            remediation_signal_snapshot_diffs.get(str(item["reason"])),
            preflight_commands=remediation_preflight_commands.get(str(item["reason"]), []),
            execute_commands=item.get("commands"),
            postcheck_commands=remediation_postcheck_commands.get(str(item["reason"]), []),
            source_confidence=(
                current_provenance_hints.get(str(item["reason"]), {}).get("source_confidence")
                if isinstance(current_provenance_hints.get(str(item["reason"])), dict)
                else (
                    previous_recommendations.get(str(item["reason"]), {}).get("source_confidence")
                    if isinstance(previous_recommendations.get(str(item["reason"])), dict)
                    else None
                )
            ),
            source_policy=(
                current_provenance_hints.get(str(item["reason"]), {}).get("source_policy")
                if isinstance(current_provenance_hints.get(str(item["reason"])), dict)
                else (
                    previous_recommendations.get(str(item["reason"]), {}).get("source_policy")
                    if isinstance(previous_recommendations.get(str(item["reason"])), dict)
                    else None
                )
            ),
            execute_signal_confidence=signal_source_confidence(
                current_signal_provenance_hints.get(str(item["reason"])),
                remediation_execute_expected_outputs.get(str(item["reason"]), []),
            ),
            postcheck_signal_confidence=signal_source_confidence(
                current_signal_provenance_hints.get(str(item["reason"])),
                remediation_postcheck_pass_signals.get(str(item["reason"]), []),
            ),
        )
        for item in remediation_order
    }
    summary["remediation_planner_summary_path"] = (
        str(remediation_planner_summary_path)
        if remediation_planner_summary_path is not None
        else None
    )
    summary["remediation_evaluator_summary_path"] = (
        str(remediation_evaluator_summary_path)
        if remediation_evaluator_summary_path is not None
        else None
    )
    summary["required_artifact_paths"] = required_artifact_paths
    summary["missing_required_artifact_paths"] = missing_required_artifact_paths
    summary["artifact_recovery_commands"] = artifact_recovery_commands
    summary["remediation_order"] = remediation_order
    summary["remediation_success_criteria"] = remediation_success_criteria
    summary["remediation_preflight_commands"] = remediation_preflight_commands
    summary["remediation_postcheck_commands"] = remediation_postcheck_commands
    summary["remediation_preflight_expected_outputs"] = remediation_preflight_expected_outputs
    summary["remediation_execute_expected_outputs"] = remediation_execute_expected_outputs
    summary["remediation_postcheck_pass_signals"] = remediation_postcheck_pass_signals
    summary["remediation_signal_snapshots_before"] = remediation_signal_snapshots_before
    summary["remediation_signal_snapshots_target"] = remediation_signal_snapshots_target
    summary["remediation_signal_snapshots_previous"] = previous_signal_snapshots
    summary["remediation_signal_snapshot_diffs"] = remediation_signal_snapshot_diffs
    summary["remediation_recommendations"] = remediation_recommendations
    summary["paper_operations_runbook_report_path"] = (
        str(out_path) if out_path is not None else None
    )
    summary["live_evidence_report_path"] = readiness.get("live_evidence_report_path")
    related_reports = _related_reports(summary)
    quick_navigation = _quick_navigation({**summary, "related_reports": related_reports})
    summary["related_reports"] = related_reports
    summary["quick_navigation"] = quick_navigation

    lines = [
        "# Scheduled Paper Operations Runbook",
        "",
        "## Current Schedule",
        "",
        f"- run_type: {summary['scheduled_run_type']}",
        f"- scheduled_for: {summary['scheduled_for']}",
        f"- command: {summary['scheduled_command']}",
        "",
        "## Current Daemon Context",
        "",
        f"- daemon_mode: {summary['daemon_mode']}",
        f"- daemon_command: {daemon_manifest.get('command')}",
        f"- state_store_path: {daemon_manifest.get('state_store_path')}",
        f"- daemon_manifest_path: {summary['daemon_manifest_path']}",
        "",
        "## Current Status",
        "",
        f"- monitoring_status: {summary['monitoring_status']}",
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
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
        f"- dashboard_status: {summary['dashboard_status']}",
        "",
        "## Current Remediation Queue",
        "",
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
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
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
            "## Required Artifacts",
            "",
            *[f"- {name}: {value}" for name, value in required_artifact_paths.items()],
            (
                "- missing_required_artifact_paths: none"
                if not missing_required_artifact_paths
                else "- missing_required_artifact_paths:"
            ),
            *[f"  - {name}" for name in missing_required_artifact_paths],
            "",
            "## Recovery Commands",
            "",
        ]
    )
    if artifact_recovery_commands:
        for name, commands in artifact_recovery_commands.items():
            lines.append(f"- {name}:")
            lines.extend(f"  - `{command}`" for command in commands)
    else:
        lines.append("- recovery_commands: none")
    lines.extend(["", "## Remediation Order", ""])
    if remediation_order:
        for item in remediation_order:
            lines.append(f"- priority_{item['priority']}: {item['reason']}")
            lines.extend(f"  - `{command}`" for command in item["commands"])
    else:
        lines.append("- remediation_order: none")
    lines.extend(["", "## Remediation Success Criteria", ""])
    if remediation_success_criteria:
        for reason, criteria in remediation_success_criteria.items():
            lines.append(f"- {reason}:")
            lines.extend(f"  - {criterion}" for criterion in criteria)
    else:
        lines.append("- remediation_success_criteria: none")
    lines.extend(["", "## Remediation Command Flow", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight:")
            for command in remediation_preflight_commands.get(reason, []):
                lines.append(f"    - `{command}`")
            lines.append("  - execute:")
            for command in item["commands"]:
                lines.append(f"    - `{command}`")
            lines.append("  - post_check:")
            for command in remediation_postcheck_commands.get(reason, []):
                lines.append(f"    - `{command}`")
    else:
        lines.append("- remediation_command_flow: none")
    lines.extend(["", "## Remediation Verification Signals", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight_expected_output:")
            for value in remediation_preflight_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - execute_expected_output:")
            for value in remediation_execute_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - postcheck_pass_signal:")
            for value in remediation_postcheck_pass_signals.get(reason, []):
                lines.append(f"    - {value}")
    else:
        lines.append("- remediation_verification_signals: none")
    lines.extend(["", "## Remediation Signal Snapshots", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - before:")
            for key, value in remediation_signal_snapshots_before.get(reason, {}).items():
                lines.append(f"    - {key}: {value}")
            lines.append("  - target:")
            for key, value in remediation_signal_snapshots_target.get(reason, {}).items():
                lines.append(f"    - {key}: {value}")
    else:
        lines.append("- remediation_signal_snapshots: none")
    lines.extend(["", "## Remediation Signal Diffs", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            for key, diff in remediation_signal_snapshot_diffs.get(reason, {}).items():
                lines.append(
                    "  - {key}: previous={previous} current={current} target={target} trend={trend} target_matched={target_matched}".format(
                        key=key,
                        previous=diff.get("previous"),
                        current=diff.get("current"),
                        target=diff.get("target"),
                        trend=diff.get("trend"),
                        target_matched=diff.get("target_matched"),
                    )
                )
    else:
        lines.append("- remediation_signal_diffs: none")
    lines.extend(["", "## Remediation Recommendations", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            recommendation = remediation_recommendations.get(reason, {})
            lines.append(f"- {reason}:")
            lines.append(f"  - status: {recommendation.get('status')}")
            lines.append(f"  - why: {recommendation.get('why')}")
            for command in recommendation.get("commands", []):
                lines.append(f"  - next: `{command}`")
    else:
        lines.append("- remediation_recommendations: none")
    lines.extend(
        [
            "",
            "## Latest Execution Lineage",
            "",
            *latest_execution_lineage_flat_lines(summary),
            "",
            "## Recommended Sequence",
            "",
            "1. Run `uv run sis refresh-operations-artifacts`.",
            "2. Review `data/reports/execution_venue_comparison.md` for cross-venue execution state.",
            "3. Review `data/reports/execution_venue_diagnostics.md` for cross-venue gaps and deltas.",
            "4. Review `data/reports/execution_gap_history.md` for gap/reaction history.",
            "5. Review `data/reports/execution_state_comparison_history.md` for diagnostics-vs-history mismatches.",
            "6. Review `data/reports/execution_snapshot_drift_history.md` for snapshot-only drift.",
            "7. Review `data/reports/execution_drift_overview.md` for the combined drift judgement.",
            "8. Review `data/reports/readiness_snapshot.md` for current phase readiness.",
            "9. Review `data/reports/remediation_scoreboard.md` for the current retry queue and blocker status.",
            "10. Review `data/reports/remediation_session_checkpoint.md` for the next action checkpoint.",
            "11. Review `data/reports/remediation_session.md` for the pending command queue.",
            "12. Review `data/reports/remediation_execution_plan.md` for staged command ordering.",
            "13. Review `data/reports/remediation_planner.md` for the current next-best command.",
            "14. Review `data/reports/operations_dashboard.md` for overall status.",
            "15. Review `data/reports/ops_review_report.md` for latest operation chain details.",
            "16. If status is acceptable, run `uv run sis paper-step` or the scheduled paper command.",
            "17. Re-run `uv run sis refresh-operations-artifacts` after the paper step.",
            "",
            "## Stop Conditions",
            "",
            "- If `monitoring_status` is `degraded`, inspect missing artifacts before continuing.",
            "- If `dashboard_status` is `blocked`, do not proceed until the latest blocked cause is understood.",
            "- If `execution_diagnostics_status` is not `ok`, inspect execution venue gaps before continuing.",
            "- If `execution_state_comparison_latest_status_match` is not `True`, inspect diagnostics/history drift before continuing.",
            "- If `execution_snapshot_drift_mismatching_snapshot_count` is not `0`, inspect snapshot-only drift before continuing.",
            "- If `execution_drift_overview_status` is not `ok`, resolve the combined drift judgement before continuing.",
            "- If `readiness_execution_ready` is not `True`, stay in the current phase and inspect readiness blockers before continuing.",
            "- If `missing_required_artifact_paths` is not empty, regenerate the missing artifacts before continuing.",
            "- If `missing_required_artifact_paths` is not empty, run the mapped commands in `Recovery Commands` before continuing.",
            "- Execute the commands in `Remediation Order` from lower priority number to higher before retrying paper operations.",
            "- If `phase_gate_strict_validation_issue_count` is not `0`, run strict artifact validation and clear the reported issues before continuing.",
            "- If the kill switch is enabled, do not run paper or live-adjacent commands.",
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
