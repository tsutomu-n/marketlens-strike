from __future__ import annotations

from typing import Any, Mapping, Sequence


_SOURCE_QUALITY_RANKS = {
    "observed_signals": 0,
    "stdout_stderr": 0,
    "exit_code": 0,
    "live_evidence_summary": 1,
    "current_state_index": 1,
    "ops_review": 1,
    "dashboard_bundle": 1,
    "timeline_summary": 1,
    "phase_gate_review": 1,
    "paper_operations_runbook": 1,
    "manifest_notes": 2,
    "markdown_reports": 2,
}


def _snapshot_target_matched(current: Any, target: Any) -> bool:
    if isinstance(target, Sequence) and not isinstance(target, (str, bytes, bytearray)):
        return current in target
    return current == target


def compare_signal_snapshots(
    previous_snapshot: Mapping[str, Any] | None,
    current_snapshot: Mapping[str, Any] | None,
    target_snapshot: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    previous = dict(previous_snapshot) if isinstance(previous_snapshot, Mapping) else {}
    current = dict(current_snapshot) if isinstance(current_snapshot, Mapping) else {}
    target = dict(target_snapshot) if isinstance(target_snapshot, Mapping) else {}
    keys = list(dict.fromkeys([*previous.keys(), *current.keys(), *target.keys()]))
    diffs: dict[str, dict[str, Any]] = {}
    for key in keys:
        previous_value = previous.get(key)
        current_value = current.get(key)
        target_value = target.get(key)
        previous_target_matched = _snapshot_target_matched(previous_value, target_value)
        current_target_matched = _snapshot_target_matched(current_value, target_value)
        if key not in previous:
            trend = "new"
        elif current_value == previous_value:
            trend = "unchanged"
        elif current_target_matched and not previous_target_matched:
            trend = "improved"
        elif previous_target_matched and not current_target_matched:
            trend = "regressed"
        else:
            trend = "changed"
        diffs[key] = {
            "previous": previous_value,
            "current": current_value,
            "target": target_value,
            "trend": trend,
            "target_matched": current_target_matched,
        }
    return diffs


def _flatten_observed_sources(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        flattened: list[str] = []
        for nested in value:
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    return []


def source_confidence_for_observed_sources(observed_sources: Sequence[str] | None) -> str | None:
    values = [str(source) for source in (observed_sources or []) if isinstance(source, str)]
    if not values:
        return None
    best_rank = min(_SOURCE_QUALITY_RANKS.get(source, 3) for source in values)
    if best_rank == 0:
        return "high"
    if best_rank == 1:
        return "medium"
    return "low"


def signal_observed_sources_by_reason(
    evaluator_summary: Mapping[str, Any] | None,
    *,
    source: str,
) -> dict[str, dict[str, Any]]:
    actions = evaluator_summary.get("actions") if isinstance(evaluator_summary, Mapping) else None
    if not isinstance(actions, Sequence):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in actions:
        if not isinstance(item, Mapping) or item.get("source") != source or not item.get("reason"):
            continue
        reason = str(item.get("reason"))
        reason_map = mapped.setdefault(reason, {})
        signal_evaluations = item.get("signal_evaluations")
        if not isinstance(signal_evaluations, Sequence):
            continue
        for signal in signal_evaluations:
            if not isinstance(signal, Mapping) or not isinstance(signal.get("signal"), str):
                continue
            reason_map[str(signal.get("signal"))] = signal.get("observed_source")
    return mapped


def signal_source_confidence(
    signal_observed_sources: Mapping[str, Any] | None,
    signals: Sequence[str] | None,
) -> str | None:
    if not isinstance(signal_observed_sources, Mapping) or not signals:
        return None
    flattened: list[str] = []
    for signal in signals:
        if not isinstance(signal, str):
            continue
        flattened.extend(_flatten_observed_sources(signal_observed_sources.get(signal)))
    return source_confidence_for_observed_sources(flattened)


def recommend_remediation_actions(
    diffs: Mapping[str, Mapping[str, Any]] | None,
    *,
    preflight_commands: Sequence[str] | None = None,
    execute_commands: Sequence[str] | None = None,
    postcheck_commands: Sequence[str] | None = None,
    source_confidence: str | None = None,
    source_policy: str | None = None,
    execute_signal_confidence: str | None = None,
    postcheck_signal_confidence: str | None = None,
) -> dict[str, Any]:
    items = dict(diffs) if isinstance(diffs, Mapping) else {}
    preflight = list(preflight_commands or [])
    execute = list(execute_commands or [])
    postcheck = list(postcheck_commands or [])
    confidence = str(source_confidence or "").strip() or None
    policy = str(source_policy or "").strip() or None
    execute_confidence = str(execute_signal_confidence or "").strip() or None
    postcheck_confidence = str(postcheck_signal_confidence or "").strip() or None
    if not items:
        response = {
            "status": "no_signals",
            "commands": [],
            "why": "no remediation signals available",
        }
        if confidence:
            response["source_confidence"] = confidence
        if policy:
            response["source_policy"] = policy
        return response
    values = [item for item in items.values() if isinstance(item, Mapping)]
    response: dict[str, Any]
    if values and all(bool(item.get("target_matched")) for item in values):
        response = {
            "status": "matched",
            "commands": postcheck,
            "why": "all current signals match target values",
        }
    elif any(item.get("trend") == "regressed" for item in values):
        response = {
            "status": "regressed",
            "commands": preflight or execute,
            "why": "one or more signals regressed away from target",
        }
    elif any(item.get("trend") in {"improved", "changed", "new"} for item in values):
        commands = execute or postcheck
        why = "signals changed but target is not fully matched yet"
        if execute_confidence == "low" or postcheck_confidence == "low":
            commands = preflight or commands
            why = "signals changed but low-confidence verification sources require revalidation before execute"
        elif confidence == "low":
            commands = preflight or commands
            why = "signals changed but low-confidence sources require revalidation before execute"
        response = {
            "status": "improving",
            "commands": commands,
            "why": why,
        }
    else:
        response = {
            "status": "stalled",
            "commands": execute or preflight,
            "why": "signals did not move toward target",
        }
    if confidence:
        response["source_confidence"] = confidence
    if policy:
        response["source_policy"] = policy
    if execute_confidence:
        response["execute_signal_confidence"] = execute_confidence
    if postcheck_confidence:
        response["postcheck_signal_confidence"] = postcheck_confidence
    return response
