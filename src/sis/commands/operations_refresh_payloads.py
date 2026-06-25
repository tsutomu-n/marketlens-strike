from __future__ import annotations

from typing import Any, cast


def remediation_planner_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    planner_rerun_diff = _dict_payload(data.get("planner_rerun_diff"))
    return {
        "planner_status": data.get("planner_status"),
        "rerun_trend": planner_rerun_diff.get("trend"),
        "next_best_command": data.get("next_best_command"),
        "next_feedback_priority_reason": _first_list_item_field(
            data,
            list_key="entries",
            field="feedback_priority_reason",
        ),
        "planned_step_count": data.get("planned_step_count"),
    }


def remediation_execution_plan_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    return {
        "execution_plan_status": data.get("execution_plan_status"),
        "next_action_command": data.get("next_action_command"),
        "next_action_feedback_priority_reason": _first_list_item_field(
            data,
            list_key="actions",
            field="feedback_priority_reason",
        ),
        "planned_action_count": data.get("planned_action_count"),
    }


def remediation_session_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    return {
        "session_status": data.get("session_status"),
        "next_pending_command": data.get("next_pending_command"),
        "next_pending_stage_signal_confidence": data.get("next_pending_stage_signal_confidence"),
        "next_pending_feedback_priority_reason": data.get("next_pending_feedback_priority_reason"),
        "pending_action_count": data.get("pending_action_count"),
    }


def remediation_session_checkpoint_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    return {
        "checkpoint_status": data.get("checkpoint_status"),
        "next_action_command": data.get("next_action_command"),
        "next_action_stage_signal_confidence": data.get("next_action_stage_signal_confidence"),
        "next_action_feedback_priority_reason": _matching_action_feedback_priority_reason(data),
        "pending_action_count": data.get("pending_action_count"),
    }


def remediation_scoreboard_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    return {
        "scoreboard_status": data.get("scoreboard_status"),
        "next_action_command": data.get("next_action_command"),
        "next_action_stage_signal_confidence": data.get("next_action_stage_signal_confidence"),
        "next_action_feedback_priority_reason": _matching_action_feedback_priority_reason(data),
        "completion_rate": data.get("completion_rate"),
    }


def remediation_evaluator_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    return {
        "evaluator_status": data.get("evaluator_status"),
        "next_action_key": data.get("next_action_key"),
        "auto_fail_count": data.get("auto_fail_count"),
    }


def remediation_evidence_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    return {
        "evidence_status": data.get("evidence_status"),
        "next_manual_review_action_key": data.get("next_manual_review_action_key"),
        "manual_review_action_count": data.get("manual_review_action_count"),
    }


def remediation_command_results_manifest_fields(payload: object) -> dict[str, object | None]:
    data = _dict_payload(payload)
    return {
        "command_results_status": data.get("command_results_status"),
        "next_unobserved_action_key": data.get("next_unobserved_action_key"),
        "missing_observation_count": data.get("missing_observation_count"),
    }


def _dict_payload(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload) if isinstance(payload, dict) else {}


def _first_list_item_field(
    payload: dict[str, Any],
    *,
    list_key: str,
    field: str,
) -> object | None:
    value = payload.get(list_key)
    if not isinstance(value, list) or not value:
        return None
    first = value[0]
    return first.get(field) if isinstance(first, dict) else None


def _matching_action_feedback_priority_reason(payload: dict[str, Any]) -> object | None:
    actions = payload.get("actions")
    next_command = payload.get("next_action_command")
    if not isinstance(actions, list):
        return None
    for item in actions:
        if isinstance(item, dict) and item.get("command") == next_command:
            return item.get("feedback_priority_reason")
    return None
