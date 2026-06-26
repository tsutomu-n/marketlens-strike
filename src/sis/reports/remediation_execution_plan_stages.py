from __future__ import annotations

__all__ = [
    "execution_plan_status",
    "feedback_priority_rank",
    "stage_order",
]


def stage_order(
    status: object,
    trend: object,
    source_confidence: object,
    *,
    feedback_priority_reason: object,
    execute_signal_confidence: str,
    postcheck_signal_confidence: str,
) -> list[str]:
    status_value = str(status or "")
    trend_value = str(trend or "")
    confidence_value = str(source_confidence or "unknown")
    feedback_value = str(feedback_priority_reason or "no_feedback")
    if status_value == "matched":
        return ["post_check"]
    if feedback_value in {"evaluation_failed", "manual_review_pending", "partial_verification"}:
        return ["preflight", "execute", "post_check"]
    if execute_signal_confidence in {"low", "unknown"} or postcheck_signal_confidence in {
        "low",
        "unknown",
    }:
        return ["preflight", "execute", "post_check"]
    if confidence_value in {"low", "unknown"}:
        return ["preflight", "execute", "post_check"]
    if status_value in {"regressed", "stalled"} or trend_value in {"regressed", "new"}:
        return ["preflight", "execute", "post_check"]
    if status_value == "improving":
        return ["execute", "post_check"]
    return ["execute", "post_check"]


def execution_plan_status(entries: list[dict]) -> str:
    statuses = [str(item.get("recommendation_status")) for item in entries]
    if not entries:
        return "no_actions"
    if any(status == "regressed" for status in statuses):
        return "regressed"
    if any(status == "stalled" for status in statuses):
        return "stalled"
    if any(status == "improving" for status in statuses):
        return "in_progress"
    if all(status == "matched" for status in statuses):
        return "postcheck_only"
    return "planned"


def feedback_priority_rank(reason: object) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(reason or "no_feedback"), 5)
