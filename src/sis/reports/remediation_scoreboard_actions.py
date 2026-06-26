from __future__ import annotations


def action_observed_sources(item: dict) -> list[str]:
    values = item.get("observed_sources")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str)]


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


def action_priority_key(item: dict) -> tuple[int, int, int, int, int, str]:
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
        str(item.get("action_key") or ""),
    )


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


def observed_source_counts(actions: list[dict]) -> dict[str, int]:
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


def feedback_priority_rank(item: dict) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(item.get("feedback_priority_reason") or "no_feedback"), 5)


def enrich_actions_with_feedback(
    actions: list[dict],
    observation_status_by_action: dict[str, str],
    evaluation_result_by_action: dict[str, str],
) -> list[dict]:
    enriched: list[dict] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        action_key = str(item.get("action_key") or "")
        observation_status = observation_status_by_action.get(action_key)
        evaluation_result = evaluation_result_by_action.get(action_key)
        enriched.append(
            {
                **item,
                "feedback_observation_status": observation_status,
                "feedback_evaluation_result": evaluation_result,
                "feedback_priority_reason": feedback_priority_reason(
                    evaluation_result,
                    observation_status,
                ),
            }
        )
    return enriched


def next_action(actions: list[dict]) -> dict | None:
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


def scoreboard_status(summary: dict, actions: list[dict]) -> str:
    if not actions:
        return "no_actions"
    fail_action_count = as_int(summary.get("fail_action_count")) or 0
    retry_action_count = as_int(summary.get("retry_action_count")) or 0
    pending_action_count = as_int(summary.get("pending_action_count")) or 0
    pass_action_count = as_int(summary.get("pass_action_count")) or 0
    if fail_action_count > 0:
        return "blocked"
    if retry_action_count > 0:
        return "retrying"
    if pending_action_count > 0:
        return "in_progress"
    if pass_action_count == len(actions):
        return "completed"
    return "in_progress"
