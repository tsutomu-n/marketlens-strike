from __future__ import annotations

from typing import Any, cast


SOURCE_QUALITY_RANKS = {
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


def entry_key(entry: dict[str, Any]) -> str:
    return f"{entry.get('source')}:{entry.get('reason')}"


def source_reason_key(source: object, reason: object) -> str:
    return f"{source}:{reason}"


def as_int(value: object) -> int | None:
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


def flatten_observed_sources(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(flatten_observed_sources(nested))
        return flattened
    if isinstance(value, list):
        flattened: list[str] = []
        for nested in value:
            flattened.extend(flatten_observed_sources(nested))
        return flattened
    return []


def evaluator_provenance_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actions = summary.get("actions")
    if not isinstance(actions, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in actions:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        key = source_reason_key(item.get("source"), item.get("reason"))
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
        observed_sources_value = entry.get("observed_sources")
        if isinstance(observed_sources_value, list):
            observed_sources = cast(list[str], observed_sources_value)
        else:
            observed_sources = []
            entry["observed_sources"] = observed_sources
        signal_observed_sources = entry.get("signal_observed_sources")
        if not isinstance(signal_observed_sources, dict):
            signal_observed_sources = {}
            entry["signal_observed_sources"] = signal_observed_sources
        supporting_action_keys_value = entry.get("supporting_action_keys")
        if isinstance(supporting_action_keys_value, list):
            supporting_action_keys = cast(list[str], supporting_action_keys_value)
        else:
            supporting_action_keys = []
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
            for source_name in flatten_observed_sources(observed_source):
                if source_name not in observed_sources:
                    observed_sources.append(source_name)
    return mapped


def source_confidence(observed_sources: object) -> str:
    if not isinstance(observed_sources, list) or not observed_sources:
        return "unknown"
    ranks = [
        SOURCE_QUALITY_RANKS.get(str(source), 3)
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


def effective_priority(base_priority: object, confidence: str, status: object) -> int:
    normalized_priority = as_int(base_priority)
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


def source_policy(confidence: str) -> str:
    if confidence == "high":
        return "direct_observation_priority"
    if confidence == "medium":
        return "structured_summary_priority"
    if confidence == "low":
        return "verify_before_execute"
    return "verify_before_execute_missing_source"


def feedback_maps(summary: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
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


def feedback_priority_reason(
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


def feedback_priority_rank(reason: object) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(reason or "no_feedback"), 5)


def recommended_command_chain(entries: list[dict[str, Any]]) -> list[str]:
    command_chain: list[str] = []
    for entry in entries:
        commands = entry.get("commands")
        if not isinstance(commands, list):
            continue
        for command in commands:
            if isinstance(command, str) and command not in command_chain:
                command_chain.append(command)
    return command_chain


def planner_status(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "no_actions"
    statuses = [str(item.get("status")) for item in entries]
    if any(status == "regressed" for status in statuses):
        return "regressed"
    if any(status == "stalled" for status in statuses):
        return "stalled"
    if any(status == "improving" for status in statuses):
        return "improving"
    if all(status == "matched" for status in statuses):
        return "matched"
    return "planned"


def planner_entries(
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
        provenance = provenance_map.get(source_reason_key(source, reason), {})
        observed_sources_value = provenance.get("observed_sources")
        observed_sources = (
            cast(list[str], observed_sources_value)
            if isinstance(observed_sources_value, list)
            else []
        )
        confidence = source_confidence(observed_sources)
        supporting_action_keys_value = provenance.get("supporting_action_keys")
        supporting_action_keys = (
            cast(list[str], supporting_action_keys_value)
            if isinstance(supporting_action_keys_value, list)
            else []
        )
        priority_reason = feedback_priority_reason(
            supporting_action_keys,
            observation_status_by_action,
            evaluation_result_by_action,
        )
        entries.append(
            {
                "source": source,
                "priority": item.get("priority"),
                "effective_priority": effective_priority(
                    item.get("priority"),
                    confidence,
                    recommendation.get("status"),
                )
                + {
                    "evaluation_failed": -2,
                    "manual_review_pending": -1,
                    "partial_verification": -1,
                    "missing_command_observation": 0,
                    "verification_passed": 1,
                    "no_feedback": 0,
                }.get(priority_reason, 0),
                "reason": reason,
                "status": recommendation.get("status"),
                "why": recommendation.get("why"),
                "commands": [command for command in commands if isinstance(command, str)]
                if isinstance(commands, list)
                else [],
                "observed_sources": observed_sources,
                "source_confidence": confidence,
                "source_policy": source_policy(confidence),
                "feedback_priority_reason": priority_reason,
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
