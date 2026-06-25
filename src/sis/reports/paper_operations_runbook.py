from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.reports.loaders import safe_read_json_dict
from sis.reports import paper_operations_runbook_paths
from sis.reports.paper_operations_runbook_remediation import (
    build_paper_operations_runbook_remediation_context,
)
from sis.reports.paper_operations_runbook_summary import (
    build_paper_operations_runbook_base_summary,
)
from sis.reports.summary_normalizers import (
    latest_execution_lineage_flat_lines,
    phase_gate_issue_preview_lines,
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
    execution = safe_read_json_dict(execution_snapshot_summary_path)
    execution_comparison = safe_read_json_dict(execution_venue_comparison_summary_path)
    execution_diagnostics = safe_read_json_dict(execution_venue_diagnostics_summary_path)
    execution_gap_history = safe_read_json_dict(execution_gap_history_summary_path)
    execution_state_comparison = safe_read_json_dict(
        execution_state_comparison_history_summary_path
    )
    execution_snapshot_drift = safe_read_json_dict(execution_snapshot_drift_history_summary_path)
    execution_drift_overview = safe_read_json_dict(execution_drift_overview_summary_path)
    readiness = safe_read_json_dict(readiness_summary_path)
    phase_gate = safe_read_json_dict(phase_gate_summary_path)
    dashboard = safe_read_json_dict(ops_dashboard_summary_path)

    summary = build_paper_operations_runbook_base_summary(
        scheduled_run_path=scheduled_run_path,
        daemon_manifest_path=daemon_manifest_path,
        monitoring_snapshot_path=monitoring_snapshot_path,
        execution_snapshot_summary_path=execution_snapshot_summary_path,
        execution_venue_comparison_summary_path=execution_venue_comparison_summary_path,
        execution_venue_diagnostics_summary_path=execution_venue_diagnostics_summary_path,
        execution_gap_history_summary_path=execution_gap_history_summary_path,
        execution_state_comparison_history_summary_path=execution_state_comparison_history_summary_path,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift_history_summary_path,
        execution_drift_overview_summary_path=execution_drift_overview_summary_path,
        readiness_summary_path=readiness_summary_path,
        phase_gate_summary_path=phase_gate_summary_path,
        ops_dashboard_summary_path=ops_dashboard_summary_path,
        scheduled_run=scheduled_run,
        daemon_manifest=daemon_manifest,
        monitoring=monitoring,
        execution=execution,
        execution_comparison=execution_comparison,
        execution_diagnostics=execution_diagnostics,
        execution_gap_history=execution_gap_history,
        execution_state_comparison=execution_state_comparison,
        execution_snapshot_drift=execution_snapshot_drift,
        execution_drift_overview=execution_drift_overview,
        readiness=readiness,
        phase_gate=phase_gate,
        dashboard=dashboard,
    )
    current_planner_summary = safe_read_json_dict(remediation_planner_summary_path)
    current_evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    remediation_context = build_paper_operations_runbook_remediation_context(
        summary=summary,
        prior_summary=prior_summary,
        planner_summary=current_planner_summary,
        evaluator_summary=current_evaluator_summary,
    )
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
    summary.update(remediation_context)
    required_artifact_paths = cast(
        dict[str, str | None], remediation_context["required_artifact_paths"]
    )
    missing_required_artifact_paths = cast(
        list[str], remediation_context["missing_required_artifact_paths"]
    )
    artifact_recovery_commands = cast(
        dict[str, list[str]], remediation_context["artifact_recovery_commands"]
    )
    remediation_order = cast(list[dict[str, Any]], remediation_context["remediation_order"])
    remediation_success_criteria = cast(
        dict[str, list[str]], remediation_context["remediation_success_criteria"]
    )
    remediation_preflight_commands = cast(
        dict[str, list[str]], remediation_context["remediation_preflight_commands"]
    )
    remediation_postcheck_commands = cast(
        dict[str, list[str]], remediation_context["remediation_postcheck_commands"]
    )
    remediation_preflight_expected_outputs = cast(
        dict[str, list[str]], remediation_context["remediation_preflight_expected_outputs"]
    )
    remediation_execute_expected_outputs = cast(
        dict[str, list[str]], remediation_context["remediation_execute_expected_outputs"]
    )
    remediation_postcheck_pass_signals = cast(
        dict[str, list[str]], remediation_context["remediation_postcheck_pass_signals"]
    )
    remediation_signal_snapshots_before = cast(
        dict[str, dict[str, object]], remediation_context["remediation_signal_snapshots_before"]
    )
    remediation_signal_snapshots_target = cast(
        dict[str, dict[str, object]], remediation_context["remediation_signal_snapshots_target"]
    )
    remediation_signal_snapshot_diffs = cast(
        dict[str, dict[str, dict[str, object]]],
        remediation_context["remediation_signal_snapshot_diffs"],
    )
    remediation_recommendations = cast(
        dict[str, dict[str, Any]], remediation_context["remediation_recommendations"]
    )
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
