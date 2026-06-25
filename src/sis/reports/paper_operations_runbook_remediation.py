from __future__ import annotations

from typing import Any, cast

from sis.reports import paper_operations_remediation
from sis.reports import paper_operations_runbook_paths
from sis.reports.summary_normalizers import (
    compare_signal_snapshots,
    recommend_remediation_actions,
    signal_observed_sources_by_reason,
    signal_source_confidence,
)


def build_paper_operations_runbook_remediation_context(
    *,
    summary: dict[str, object],
    prior_summary: dict[str, object],
    planner_summary: dict[str, object],
    evaluator_summary: dict[str, object],
) -> dict[str, object]:
    required_artifact_paths = paper_operations_runbook_paths.required_artifact_paths(summary)
    missing_required_artifact_paths = [
        key for key, value in required_artifact_paths.items() if not value
    ]
    artifact_recovery_commands = paper_operations_remediation.artifact_recovery_commands(
        missing_required_artifact_paths
    )
    remediation_order = paper_operations_remediation.remediation_order(
        summary,
        missing_required_artifact_paths,
        artifact_recovery_commands,
    )
    remediation_success_criteria = {
        item["reason"]: paper_operations_remediation.remediation_success_criteria(
            str(item["reason"])
        )
        for item in remediation_order
    }
    remediation_preflight_commands = {
        item["reason"]: paper_operations_remediation.remediation_preflight_commands(
            str(item["reason"])
        )
        for item in remediation_order
    }
    remediation_postcheck_commands = {
        item["reason"]: paper_operations_remediation.remediation_postcheck_commands(
            str(item["reason"])
        )
        for item in remediation_order
    }
    remediation_preflight_expected_outputs = {
        item["reason"]: paper_operations_remediation.remediation_preflight_expected_outputs(
            str(item["reason"])
        )
        for item in remediation_order
    }
    remediation_execute_expected_outputs = {
        item["reason"]: paper_operations_remediation.remediation_execute_expected_outputs(
            str(item["reason"])
        )
        for item in remediation_order
    }
    remediation_postcheck_pass_signals = {
        item["reason"]: paper_operations_remediation.remediation_postcheck_pass_signals(
            str(item["reason"])
        )
        for item in remediation_order
    }
    remediation_signal_snapshots_before = {
        item["reason"]: paper_operations_remediation.remediation_signal_snapshot_before(
            str(item["reason"]), summary
        )
        for item in remediation_order
    }
    remediation_signal_snapshots_target = {
        item["reason"]: paper_operations_remediation.remediation_signal_snapshot_target(
            str(item["reason"])
        )
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
    current_planner_entries_value = planner_summary.get("entries")
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
        evaluator_summary,
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
    return {
        "required_artifact_paths": required_artifact_paths,
        "missing_required_artifact_paths": missing_required_artifact_paths,
        "artifact_recovery_commands": artifact_recovery_commands,
        "remediation_order": remediation_order,
        "remediation_success_criteria": remediation_success_criteria,
        "remediation_preflight_commands": remediation_preflight_commands,
        "remediation_postcheck_commands": remediation_postcheck_commands,
        "remediation_preflight_expected_outputs": remediation_preflight_expected_outputs,
        "remediation_execute_expected_outputs": remediation_execute_expected_outputs,
        "remediation_postcheck_pass_signals": remediation_postcheck_pass_signals,
        "remediation_signal_snapshots_before": remediation_signal_snapshots_before,
        "remediation_signal_snapshots_target": remediation_signal_snapshots_target,
        "remediation_signal_snapshots_previous": previous_signal_snapshots,
        "remediation_signal_snapshot_diffs": remediation_signal_snapshot_diffs,
        "remediation_recommendations": remediation_recommendations,
    }
