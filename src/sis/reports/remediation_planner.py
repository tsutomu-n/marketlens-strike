from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.storage.jsonl_store import read_jsonl
from sis.reports.loaders import safe_read_json_dict
from sis.storage.jsonl_store import write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_planner_report": str(out_path),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_planner_report": str(out_path),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _entry_key(entry: dict[str, Any]) -> str:
    return f"{entry.get('source')}:{entry.get('reason')}"


def _source_reason_key(source: object, reason: object) -> str:
    return f"{source}:{reason}"


def _planner_status_rank(status: object) -> int:
    ranks = {
        "matched": 0,
        "no_actions": 0,
        "improving": 1,
        "planned": 1,
        "stalled": 2,
        "regressed": 3,
    }
    return ranks.get(str(status), 99)


_SOURCE_QUALITY_RANKS = {
    "observed_signals": 0,
    "stdout_stderr": 0,
    "exit_code": 0,
    "live_evidence_summary": 1,
    "current_state_index": 1,
    "ops_review": 1,
    "dashboard_bundle": 1,
    "timeline_summary": 1,
    "manifest_notes": 2,
    "markdown_reports": 2,
}


def _note_map(notes: object) -> dict[str, str]:
    if not isinstance(notes, list):
        return {}
    mapped: dict[str, str] = {}
    for note in notes:
        if not isinstance(note, str) or "=" not in note:
            continue
        key, value = note.split("=", 1)
        mapped[key] = value
    return mapped


def _latest_planner_manifest(operation_chain_path: Path | None) -> dict[str, Any]:
    if operation_chain_path is None or not operation_chain_path.exists():
        return {}
    latest: dict[str, Any] = {}
    for item in read_jsonl(operation_chain_path):
        if isinstance(item, dict) and item.get("operation") == "remediation_planner_dry_run":
            latest = cast(dict[str, Any], item)
    return latest


def _flatten_observed_sources(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    if isinstance(value, list):
        flattened: list[str] = []
        for nested in value:
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    return []


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _evaluator_provenance_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actions = summary.get("actions")
    if not isinstance(actions, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in actions:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        key = _source_reason_key(item.get("source"), item.get("reason"))
        if key == ":":
            continue
        entry = mapped.get(key)
        if not isinstance(entry, dict):
            entry = {
                "observed_sources": [],
                "signal_observed_sources": {},
                "supporting_action_keys": [],
            }
            mapped[key] = dict(entry)
        observed_sources = entry.get("observed_sources")
        if not isinstance(observed_sources, list):
            observed_sources: list[str] = []
            entry["observed_sources"] = observed_sources
        signal_observed_sources = entry.get("signal_observed_sources")
        if not isinstance(signal_observed_sources, dict):
            signal_observed_sources = {}
            entry["signal_observed_sources"] = signal_observed_sources
        supporting_action_keys = entry.get("supporting_action_keys")
        if not isinstance(supporting_action_keys, list):
            supporting_action_keys: list[str] = []
            entry["supporting_action_keys"] = supporting_action_keys
        action_key = item.get("action_key")
        if isinstance(action_key, str) and action_key not in supporting_action_keys:
            supporting_action_keys.append(action_key)
        signal_evaluations = item.get("signal_evaluations")
        if not isinstance(signal_evaluations, list):
            continue
        for signal in signal_evaluations:
            if not isinstance(signal, dict):
                continue
            signal_name = signal.get("signal")
            observed_source = signal.get("observed_source")
            if isinstance(signal_name, str) and observed_source is not None:
                signal_observed_sources[signal_name] = observed_source
            for source_name in _flatten_observed_sources(observed_source):
                if source_name not in observed_sources:
                    observed_sources.append(source_name)
    return mapped


def _source_confidence(observed_sources: object) -> str:
    if not isinstance(observed_sources, list) or not observed_sources:
        return "unknown"
    ranks = [
        _SOURCE_QUALITY_RANKS.get(str(source), 3)
        for source in observed_sources
        if isinstance(source, str)
    ]
    if not ranks:
        return "unknown"
    best_rank = min(ranks)
    if best_rank == 0:
        return "high"
    if best_rank == 1:
        return "medium"
    return "low"


def _effective_priority(base_priority: object, confidence: str, status: object) -> int:
    normalized_priority = _as_int(base_priority)
    if normalized_priority is None:
        normalized_priority = 999
    if confidence == "high":
        if str(status) in {"regressed", "stalled"}:
            return max(1, normalized_priority - 1)
        return normalized_priority
    if confidence == "medium":
        return normalized_priority
    if confidence == "low":
        return normalized_priority + 1
    return normalized_priority + 2


def _source_policy(confidence: str) -> str:
    if confidence == "high":
        return "direct_observation_priority"
    if confidence == "medium":
        return "structured_summary_priority"
    if confidence == "low":
        return "verify_before_execute"
    return "verify_before_execute_missing_source"


def _feedback_maps(summary: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    entries_value = summary.get("entries")
    entries = cast(list[object], entries_value) if isinstance(entries_value, list) else []
    observation_status_by_action: dict[str, str] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        action_key = item.get("action_key")
        observation_status = item.get("observation_status")
        if isinstance(action_key, str) and isinstance(observation_status, str):
            observation_status_by_action[action_key] = observation_status
    actions_value = summary.get("actions")
    actions = cast(list[object], actions_value) if isinstance(actions_value, list) else []
    evaluation_result_by_action: dict[str, str] = {}
    for item in actions:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        action_key = item.get("action_key")
        evaluation_result = item.get("evaluation_result")
        if isinstance(action_key, str) and isinstance(evaluation_result, str):
            evaluation_result_by_action[action_key] = evaluation_result
    return observation_status_by_action, evaluation_result_by_action


def _feedback_priority_reason(
    supporting_action_keys: list[str],
    observation_status_by_action: dict[str, str],
    evaluation_result_by_action: dict[str, str],
) -> str:
    evaluation_results = [
        evaluation_result_by_action.get(key)
        for key in supporting_action_keys
        if isinstance(evaluation_result_by_action.get(key), str)
    ]
    observation_statuses = [
        observation_status_by_action.get(key)
        for key in supporting_action_keys
        if isinstance(observation_status_by_action.get(key), str)
    ]
    if any(value == "fail" for value in evaluation_results):
        return "evaluation_failed"
    if any(value == "manual_review" for value in evaluation_results):
        return "manual_review_pending"
    if any(value == "partial" for value in evaluation_results):
        return "partial_verification"
    if supporting_action_keys and any(value != "observed" for value in observation_statuses):
        return "missing_command_observation"
    if any(value == "pass" for value in evaluation_results):
        return "verification_passed"
    return "no_feedback"


def _feedback_priority_rank(reason: object) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(reason or "no_feedback"), 5)


def _planner_entries(
    summary: dict[str, Any],
    *,
    source: str,
    provenance_map: dict[str, dict[str, Any]],
    observation_status_by_action: dict[str, str],
    evaluation_result_by_action: dict[str, str],
) -> list[dict[str, Any]]:
    order = summary.get("remediation_order")
    recommendations = summary.get("remediation_recommendations")
    if not isinstance(order, list) or not isinstance(recommendations, dict):
        return []
    recommendations = cast(dict[str, Any], recommendations)
    entries: list[dict[str, Any]] = []
    for item in order:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        reason = str(item.get("reason") or "")
        if not reason:
            continue
        recommendation = recommendations.get(reason)
        if not isinstance(recommendation, dict):
            recommendation = {}
        recommendation = cast(dict[str, Any], recommendation)
        commands = recommendation.get("commands")
        provenance = provenance_map.get(_source_reason_key(source, reason), {})
        observed_sources_value = provenance.get("observed_sources")
        observed_sources = (
            cast(list[str], observed_sources_value)
            if isinstance(observed_sources_value, list)
            else []
        )
        source_confidence = _source_confidence(observed_sources)
        supporting_action_keys_value = provenance.get("supporting_action_keys")
        supporting_action_keys = (
            cast(list[str], supporting_action_keys_value)
            if isinstance(supporting_action_keys_value, list)
            else []
        )
        feedback_priority_reason = _feedback_priority_reason(
            supporting_action_keys,
            observation_status_by_action,
            evaluation_result_by_action,
        )
        entries.append(
            {
                "source": source,
                "priority": item.get("priority"),
                "effective_priority": _effective_priority(
                    item.get("priority"),
                    source_confidence,
                    recommendation.get("status"),
                )
                + {
                    "evaluation_failed": -2,
                    "manual_review_pending": -1,
                    "partial_verification": -1,
                    "missing_command_observation": 0,
                    "verification_passed": 1,
                    "no_feedback": 0,
                }.get(feedback_priority_reason, 0),
                "reason": reason,
                "status": recommendation.get("status"),
                "why": recommendation.get("why"),
                "commands": [command for command in commands if isinstance(command, str)]
                if isinstance(commands, list)
                else [],
                "observed_sources": observed_sources,
                "source_confidence": source_confidence,
                "source_policy": _source_policy(source_confidence),
                "feedback_priority_reason": feedback_priority_reason,
                "feedback_observation_statuses": {
                    key: observation_status_by_action.get(key)
                    for key in supporting_action_keys
                    if isinstance(key, str) and key in observation_status_by_action
                },
                "feedback_evaluation_results": {
                    key: evaluation_result_by_action.get(key)
                    for key in supporting_action_keys
                    if isinstance(key, str) and key in evaluation_result_by_action
                },
                "signal_observed_sources": (
                    provenance.get("signal_observed_sources")
                    if isinstance(provenance.get("signal_observed_sources"), dict)
                    else {}
                ),
                "supporting_action_keys": supporting_action_keys,
            }
        )
    return entries


def _planner_entry_diffs(
    previous_entries: object, current_entries: list[dict]
) -> dict[str, dict[str, object]]:
    previous_list = previous_entries if isinstance(previous_entries, list) else []
    previous = {
        _entry_key(item): item
        for item in previous_list
        if isinstance(item, dict) and _entry_key(item)
    }
    current = {
        _entry_key(item): item
        for item in current_entries
        if isinstance(item, dict) and _entry_key(item)
    }
    diffs: dict[str, dict[str, object]] = {}
    for key in sorted(set(previous) | set(current)):
        previous_entry = previous.get(key, {})
        current_entry = current.get(key, {})
        previous_status = previous_entry.get("status")
        current_status = current_entry.get("status")
        previous_commands = (
            previous_entry.get("commands")
            if isinstance(previous_entry.get("commands"), list)
            else []
        )
        current_commands = (
            current_entry.get("commands") if isinstance(current_entry.get("commands"), list) else []
        )
        if not previous_entry:
            trend = "new"
        elif not current_entry:
            trend = "removed"
        elif previous_status == current_status and previous_commands == current_commands:
            trend = "unchanged"
        elif _planner_status_rank(current_status) < _planner_status_rank(previous_status):
            trend = "improved"
        elif _planner_status_rank(current_status) > _planner_status_rank(previous_status):
            trend = "regressed"
        else:
            trend = "changed"
        diffs[key] = {
            "source": current_entry.get("source") or previous_entry.get("source"),
            "reason": current_entry.get("reason") or previous_entry.get("reason"),
            "previous_status": previous_status,
            "current_status": current_status,
            "previous_commands": previous_commands,
            "current_commands": current_commands,
            "trend": trend,
            "active": bool(current_entry),
        }
    return diffs


def _command_chain_diff(previous_chain: object, current_chain: list[str]) -> dict[str, object]:
    previous = (
        [item for item in previous_chain if isinstance(item, str)]
        if isinstance(previous_chain, list)
        else []
    )
    added = [item for item in current_chain if item not in previous]
    removed = [item for item in previous if item not in current_chain]
    unchanged = [item for item in current_chain if item in previous]
    if not previous:
        trend = "first_run"
    elif not added and not removed:
        trend = "unchanged"
    elif removed and not added:
        trend = "narrowed"
    elif added and not removed:
        trend = "expanded"
    else:
        trend = "changed"
    return {
        "previous": previous,
        "current": current_chain,
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "trend": trend,
    }


def _planner_rerun_diff(
    previous_summary: dict,
    previous_manifest: dict,
    *,
    planner_status: str,
    planned_step_count: int,
    next_best_command: str | None,
    recommended_command_chain: list[str],
) -> dict[str, object]:
    previous_notes = _note_map(previous_manifest.get("notes"))
    previous_status = previous_summary.get("planner_status") or previous_manifest.get("status")
    previous_next_best_command = previous_summary.get("next_best_command") or previous_notes.get(
        "next_best_command"
    )
    previous_planned_step_count_raw = previous_summary.get(
        "planned_step_count"
    ) or previous_notes.get("planned_step_count")
    previous_planned_step_count = _as_int(previous_planned_step_count_raw)
    if not previous_summary and not previous_manifest:
        trend = "first_run"
    elif (
        previous_status == planner_status
        and previous_next_best_command == next_best_command
        and previous_planned_step_count == planned_step_count
    ):
        trend = "unchanged"
    elif _planner_status_rank(planner_status) < _planner_status_rank(previous_status):
        trend = "improved"
    elif _planner_status_rank(planner_status) > _planner_status_rank(previous_status):
        trend = "regressed"
    elif (
        previous_planned_step_count is not None and planned_step_count < previous_planned_step_count
    ):
        trend = "improved"
    elif (
        previous_planned_step_count is not None and planned_step_count > previous_planned_step_count
    ):
        trend = "regressed"
    else:
        trend = "changed"
    return {
        "previous_summary_path": previous_summary.get("remediation_planner_report_path"),
        "previous_manifest_run_id": previous_manifest.get("run_id"),
        "previous_summary_status": previous_summary.get("planner_status"),
        "previous_manifest_status": previous_manifest.get("status"),
        "current_status": planner_status,
        "previous_next_best_command": previous_next_best_command,
        "current_next_best_command": next_best_command,
        "previous_planned_step_count": previous_planned_step_count,
        "current_planned_step_count": planned_step_count,
        "trend": trend,
        "command_chain_diff": _command_chain_diff(
            previous_summary.get("recommended_command_chain"),
            recommended_command_chain,
        ),
    }


def build_remediation_planner(
    *,
    phase_gate_summary_path: Path | None = None,
    runbook_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    remediation_command_results_summary_path: Path | None = None,
    operation_chain_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    previous_summary = safe_read_json_dict(summary_path)
    previous_manifest = _latest_planner_manifest(operation_chain_path)
    phase_gate_summary = safe_read_json_dict(phase_gate_summary_path)
    runbook_summary = safe_read_json_dict(runbook_summary_path)
    evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    command_results_summary = safe_read_json_dict(remediation_command_results_summary_path)
    evaluator_provenance = _evaluator_provenance_map(evaluator_summary)
    observation_status_by_action, evaluation_result_by_action = _feedback_maps(
        {
            "entries": command_results_summary.get("entries"),
            "actions": evaluator_summary.get("actions"),
        }
    )
    entries = [
        *_planner_entries(
            phase_gate_summary,
            source="phase_gate_review",
            provenance_map=evaluator_provenance,
            observation_status_by_action=observation_status_by_action,
            evaluation_result_by_action=evaluation_result_by_action,
        ),
        *_planner_entries(
            runbook_summary,
            source="paper_operations_runbook",
            provenance_map=evaluator_provenance,
            observation_status_by_action=observation_status_by_action,
            evaluation_result_by_action=evaluation_result_by_action,
        ),
    ]
    entries.sort(
        key=lambda item: (
            _feedback_priority_rank(item.get("feedback_priority_reason")),
            _as_int(item.get("effective_priority")) or 999,
            _as_int(item.get("priority")) or 999,
            str(item.get("source")),
            str(item.get("reason")),
        )
    )

    recommended_command_chain: list[str] = []
    for entry in entries:
        for command in entry.get("commands", []):
            if isinstance(command, str) and command not in recommended_command_chain:
                recommended_command_chain.append(command)

    next_best_command = recommended_command_chain[0] if recommended_command_chain else None
    planner_status = "no_actions"
    if entries:
        statuses = [str(item.get("status")) for item in entries]
        if any(status == "regressed" for status in statuses):
            planner_status = "regressed"
        elif any(status == "stalled" for status in statuses):
            planner_status = "stalled"
        elif any(status == "improving" for status in statuses):
            planner_status = "improving"
        elif all(status == "matched" for status in statuses):
            planner_status = "matched"
        else:
            planner_status = "planned"

    planner_rerun_diff = _planner_rerun_diff(
        previous_summary,
        previous_manifest,
        planner_status=planner_status,
        planned_step_count=len(entries),
        next_best_command=next_best_command,
        recommended_command_chain=recommended_command_chain,
    )
    planner_entry_diffs = _planner_entry_diffs(previous_summary.get("entries"), entries)
    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path)

    summary = {
        "planner_status": planner_status,
        "planned_step_count": len(entries),
        "next_best_command": next_best_command,
        "source_policy_summary": {
            _entry_key(item): {
                "source_confidence": item.get("source_confidence"),
                "source_policy": item.get("source_policy"),
                "effective_priority": item.get("effective_priority"),
            }
            for item in entries
        },
        "recommended_command_chain": recommended_command_chain,
        "phase_gate_summary_path": str(phase_gate_summary_path)
        if phase_gate_summary_path is not None
        else None,
        "runbook_summary_path": str(runbook_summary_path)
        if runbook_summary_path is not None
        else None,
        "remediation_evaluator_summary_path": (
            str(remediation_evaluator_summary_path)
            if remediation_evaluator_summary_path is not None
            else None
        ),
        "remediation_command_results_summary_path": (
            str(remediation_command_results_summary_path)
            if remediation_command_results_summary_path is not None
            else None
        ),
        "operation_chain_path": str(operation_chain_path)
        if operation_chain_path is not None
        else None,
        "previous_planner_status": previous_summary.get("planner_status")
        or previous_manifest.get("status"),
        "previous_planner_manifest_run_id": previous_manifest.get("run_id"),
        "planner_rerun_diff": planner_rerun_diff,
        "planner_entry_diffs": planner_entry_diffs,
        "entries": entries,
        "quick_navigation": quick_navigation,
        "related_reports": related_reports,
        "remediation_planner_report_path": str(out_path) if out_path is not None else None,
    }
    command_chain_diff = (
        planner_rerun_diff.get("command_chain_diff")
        if isinstance(planner_rerun_diff.get("command_chain_diff"), dict)
        else {}
    )
    chain_trend = command_chain_diff.get("trend")
    chain_added = command_chain_diff.get("added")
    chain_removed = command_chain_diff.get("removed")
    chain_unchanged = command_chain_diff.get("unchanged")

    lines = ["# Remediation Planner Dry Run", ""]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(
        [
            "## Planner Summary",
            "",
            f"- planner_status: {summary['planner_status']}",
            f"- planned_step_count: {summary['planned_step_count']}",
            f"- next_best_command: {summary['next_best_command']}",
            f"- phase_gate_summary_path: {summary['phase_gate_summary_path']}",
            f"- runbook_summary_path: {summary['runbook_summary_path']}",
            f"- remediation_evaluator_summary_path: {summary['remediation_evaluator_summary_path']}",
            f"- remediation_command_results_summary_path: {summary['remediation_command_results_summary_path']}",
            f"- operation_chain_path: {summary['operation_chain_path']}",
            "",
            "## Recommended Command Chain",
            "",
        ]
    )
    if recommended_command_chain:
        lines.extend(f"- `{command}`" for command in recommended_command_chain)
    else:
        lines.append("- recommended_command_chain: none")

    lines.extend(
        [
            "",
            "## Planner Rerun Diff",
            "",
            f"- trend: {planner_rerun_diff['trend']}",
            f"- previous_summary_status: {planner_rerun_diff['previous_summary_status']}",
            f"- previous_manifest_status: {planner_rerun_diff['previous_manifest_status']}",
            f"- current_status: {planner_rerun_diff['current_status']}",
            f"- previous_next_best_command: {planner_rerun_diff['previous_next_best_command']}",
            f"- current_next_best_command: {planner_rerun_diff['current_next_best_command']}",
            f"- previous_planned_step_count: {planner_rerun_diff['previous_planned_step_count']}",
            f"- current_planned_step_count: {planner_rerun_diff['current_planned_step_count']}",
            f"- previous_manifest_run_id: {planner_rerun_diff['previous_manifest_run_id']}",
            "",
            "## Recommended Command Chain Diff",
            "",
            f"- trend: {chain_trend}",
            f"- added: {chain_added}",
            f"- removed: {chain_removed}",
            f"- unchanged: {chain_unchanged}",
            "",
            "## Planner Entry Diffs",
            "",
        ]
    )
    if planner_entry_diffs:
        for key, diff in planner_entry_diffs.items():
            lines.append(f"- {key}: {diff['trend']}")
            lines.append(f"  - previous_status: {diff['previous_status']}")
            lines.append(f"  - current_status: {diff['current_status']}")
            lines.append(f"  - previous_commands: {diff['previous_commands']}")
            lines.append(f"  - current_commands: {diff['current_commands']}")
            lines.append(f"  - active: {diff['active']}")
    else:
        lines.append("- planner_entry_diffs: none")

    lines.extend(["", "## Planned Steps", ""])
    if entries:
        for entry in entries:
            lines.append(f"- priority_{entry['priority']}_{entry['source']}: {entry['reason']}")
            lines.append(f"  - status: {entry['status']}")
            lines.append(f"  - why: {entry['why']}")
            lines.append(f"  - effective_priority: {entry['effective_priority']}")
            lines.append(f"  - observed_sources: {entry['observed_sources']}")
            lines.append(f"  - source_confidence: {entry['source_confidence']}")
            lines.append(f"  - source_policy: {entry['source_policy']}")
            lines.append(f"  - feedback_priority_reason: {entry['feedback_priority_reason']}")
            lines.append(f"  - supporting_action_keys: {entry['supporting_action_keys']}")
            for command in entry["commands"]:
                lines.append(f"  - next: `{command}`")
    else:
        lines.append("- planned_steps: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
