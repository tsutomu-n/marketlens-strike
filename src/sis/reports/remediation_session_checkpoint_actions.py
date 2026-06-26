from __future__ import annotations

from typing import Any, cast


VALID_RESULTS = {"pending", "pass", "fail", "retry"}


def action_observed_sources(item: dict[str, Any]) -> list[str]:
    values = item.get("observed_sources")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str)]


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


def confidence_rank(value: object) -> int:
    return {
        "unknown": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }.get(str(value or "unknown"), 0)


def stage_rank(value: object) -> int:
    return {
        "preflight": 0,
        "execute": 1,
        "post_check": 2,
    }.get(str(value or ""), 99)


def action_priority_key(item: dict[str, Any]) -> tuple[int, int, int, int, int, str, str]:
    effective_priority = as_int(item.get("effective_priority"))
    priority = as_int(item.get("priority"))
    sequence = as_int(item.get("sequence")) or 0
    return (
        effective_priority
        if effective_priority is not None
        else (priority if priority is not None else 999),
        priority if priority is not None else 999,
        stage_rank(item.get("stage")),
        confidence_rank(item.get("stage_signal_confidence")),
        sequence,
        str(item.get("source") or ""),
        str(item.get("reason") or ""),
    )


def observed_source_counts(actions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in actions:
        if not isinstance(item, dict):
            continue
        for source in action_observed_sources(item):
            counts[source] = counts.get(source, 0) + 1
    return counts


def feedback_priority_reason(evaluation_result: object, observation_status: object) -> str:
    evaluation_value = str(evaluation_result or "")
    observation_value = str(observation_status or "")
    if evaluation_value == "fail":
        return "evaluation_failed"
    if evaluation_value == "manual_review":
        return "manual_review_pending"
    if evaluation_value == "partial":
        return "partial_verification"
    if observation_value != "observed":
        return "missing_command_observation"
    if evaluation_value == "pass":
        return "verification_passed"
    return "no_feedback"


def feedback_priority_rank(item: dict[str, Any]) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(item.get("feedback_priority_reason") or "no_feedback"), 5)


def enrich_actions_with_feedback(
    actions: list[dict[str, Any]],
    observation_status_by_action: dict[str, str],
    evaluation_result_by_action: dict[str, str],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        action_key = str(item.get("action_key") or "")
        observation_status = observation_status_by_action.get(action_key)
        evaluation_result = evaluation_result_by_action.get(action_key)
        priority_reason = feedback_priority_reason(
            evaluation_result,
            observation_status,
        )
        enriched.append(
            {
                **item,
                "feedback_observation_status": observation_status,
                "feedback_evaluation_result": evaluation_result,
                "feedback_priority_reason": priority_reason,
            }
        )
    return enriched


def next_action(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        item
        for item in actions
        if isinstance(item, dict) and item.get("checkpoint_status") in {"retry", "pending"}
    ]
    if not candidates:
        return None
    status_rank = {"retry": 0, "pending": 1}
    return min(
        candidates,
        key=lambda item: (
            status_rank.get(str(item.get("checkpoint_status") or ""), 99),
            feedback_priority_rank(item),
            *action_priority_key(item),
        ),
    )


def merge_actions(
    session_actions: object,
    previous_actions: object,
    *,
    action_key: str | None = None,
    result: str | None = None,
    note: str | None = None,
    evidence_path: str | None = None,
    observed_signal: str | None = None,
    stdout_summary: str | None = None,
    stderr_summary: str | None = None,
    exit_code: int | None = None,
) -> list[dict[str, Any]]:
    current = session_actions if isinstance(session_actions, list) else []
    previous_list = previous_actions if isinstance(previous_actions, list) else []
    previous = {
        str(cast(dict[str, Any], item).get("action_key")): cast(dict[str, Any], item)
        for item in previous_list
        if isinstance(item, dict) and cast(dict[str, Any], item).get("action_key")
    }
    merged: list[dict[str, Any]] = []
    for item in current:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        key = str(item.get("action_key") or "")
        previous_item = previous.get(key, {})
        checkpoint_status = previous_item.get("checkpoint_status") or "pending"
        if key == action_key and result in VALID_RESULTS:
            checkpoint_status = result
        evidence_status = (
            previous_item.get("evidence_status")
            or item.get("evidence_status")
            or "evidence_missing"
        )
        if checkpoint_status == "pass":
            evidence_status = "evidence_recorded"
        elif checkpoint_status in {"fail", "retry"}:
            evidence_status = "needs_review"
        operator_notes_value = previous_item.get("operator_notes")
        operator_notes: list[object] = (
            cast(list[object], operator_notes_value)
            if isinstance(operator_notes_value, list)
            else []
        )
        if key == action_key and note:
            operator_notes = [*operator_notes, note]
        evidence_paths_value = previous_item.get("evidence_paths")
        evidence_paths: list[object] = (
            cast(list[object], evidence_paths_value)
            if isinstance(evidence_paths_value, list)
            else []
        )
        if key == action_key and evidence_path:
            evidence_paths = [*evidence_paths, evidence_path]
        observed_signals_value = previous_item.get("observed_signals")
        observed_signals: list[object] = (
            cast(list[object], observed_signals_value)
            if isinstance(observed_signals_value, list)
            else []
        )
        if key == action_key and observed_signal:
            observed_signals = [*observed_signals, observed_signal]
        command_result_records_value = previous_item.get("command_result_records")
        command_result_records: list[object] = (
            cast(list[object], command_result_records_value)
            if isinstance(command_result_records_value, list)
            else []
        )
        latest_exit_code = previous_item.get("latest_exit_code")
        latest_stdout_summary = previous_item.get("latest_stdout_summary")
        latest_stderr_summary = previous_item.get("latest_stderr_summary")
        if key == action_key and any(
            value is not None
            for value in (evidence_path, observed_signal, stdout_summary, stderr_summary, exit_code)
        ):
            record: dict[str, object] = {}
            if evidence_path:
                record["evidence_path"] = evidence_path
            if observed_signal:
                record["observed_signal"] = observed_signal
            if stdout_summary:
                record["stdout_summary"] = stdout_summary
            if stderr_summary:
                record["stderr_summary"] = stderr_summary
            if exit_code is not None:
                record["exit_code"] = exit_code
            if result:
                record["checkpoint_result"] = result
            command_result_records = [*command_result_records, record]
            if exit_code is not None:
                latest_exit_code = exit_code
            if stdout_summary:
                latest_stdout_summary = stdout_summary
            if stderr_summary:
                latest_stderr_summary = stderr_summary
        merged.append(
            {
                **item,
                "checkpoint_status": checkpoint_status,
                "evidence_status": evidence_status,
                "operator_notes": operator_notes,
                "evidence_paths": list(
                    dict.fromkeys(str(value) for value in evidence_paths if isinstance(value, str))
                ),
                "observed_signals": list(
                    dict.fromkeys(
                        str(value) for value in observed_signals if isinstance(value, str)
                    )
                ),
                "latest_exit_code": latest_exit_code,
                "latest_stdout_summary": latest_stdout_summary,
                "latest_stderr_summary": latest_stderr_summary,
                "command_result_records": command_result_records,
            }
        )
    return merged


def checkpoint_summary_status(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "no_actions"
    statuses = [str(item.get("checkpoint_status")) for item in actions]
    if any(status == "fail" for status in statuses):
        return "attention_required"
    if any(status == "retry" for status in statuses):
        return "retry_pending"
    if all(status == "pass" for status in statuses):
        return "completed"
    return "in_progress"
