from __future__ import annotations

from sis.commands.operations_refresh_payloads import (
    remediation_command_results_manifest_fields,
    remediation_evaluator_manifest_fields,
    remediation_evidence_manifest_fields,
    remediation_execution_plan_manifest_fields,
    remediation_planner_manifest_fields,
    remediation_scoreboard_manifest_fields,
    remediation_session_checkpoint_manifest_fields,
    remediation_session_manifest_fields,
)


def test_remediation_planner_and_execution_plan_manifest_fields() -> None:
    planner_payload = {
        "planner_status": "regressed",
        "planner_rerun_diff": {"trend": "improved"},
        "next_best_command": "uv run sis refresh-operations-artifacts",
        "planned_step_count": 3,
        "entries": [{"feedback_priority_reason": "evaluation_failed"}],
    }
    execution_payload = {
        "execution_plan_status": "stalled",
        "next_action_command": "uv run sis monitoring-status",
        "planned_action_count": 2,
        "actions": [{"feedback_priority_reason": "verification_passed"}],
    }

    assert remediation_planner_manifest_fields(planner_payload) == {
        "planner_status": "regressed",
        "rerun_trend": "improved",
        "next_best_command": "uv run sis refresh-operations-artifacts",
        "next_feedback_priority_reason": "evaluation_failed",
        "planned_step_count": 3,
    }
    assert remediation_execution_plan_manifest_fields(execution_payload) == {
        "execution_plan_status": "stalled",
        "next_action_command": "uv run sis monitoring-status",
        "next_action_feedback_priority_reason": "verification_passed",
        "planned_action_count": 2,
    }


def test_remediation_session_checkpoint_and_scoreboard_match_action_feedback() -> None:
    checkpoint_payload = {
        "checkpoint_status": "retry_pending",
        "next_action_command": "uv run sis validate-artifacts --strict",
        "next_action_stage_signal_confidence": "low",
        "pending_action_count": 1,
        "actions": [
            {
                "command": "uv run sis monitoring-status",
                "feedback_priority_reason": "wrong_action",
            },
            {
                "command": "uv run sis validate-artifacts --strict",
                "feedback_priority_reason": "evaluation_failed",
            },
        ],
    }
    scoreboard_payload = {
        "scoreboard_status": "retrying",
        "next_action_command": "uv run sis phase-gate-review",
        "next_action_stage_signal_confidence": "high",
        "completion_rate": 0.75,
        "actions": [
            {
                "command": "uv run sis phase-gate-review",
                "feedback_priority_reason": "verification_passed",
            }
        ],
    }

    assert remediation_session_checkpoint_manifest_fields(checkpoint_payload) == {
        "checkpoint_status": "retry_pending",
        "next_action_command": "uv run sis validate-artifacts --strict",
        "next_action_stage_signal_confidence": "low",
        "next_action_feedback_priority_reason": "evaluation_failed",
        "pending_action_count": 1,
    }
    assert remediation_scoreboard_manifest_fields(scoreboard_payload) == {
        "scoreboard_status": "retrying",
        "next_action_command": "uv run sis phase-gate-review",
        "next_action_stage_signal_confidence": "high",
        "next_action_feedback_priority_reason": "verification_passed",
        "completion_rate": 0.75,
    }


def test_remediation_payload_selectors_preserve_none_for_malformed_inputs() -> None:
    malformed = {"entries": {}, "actions": {}, "planner_rerun_diff": "bad"}

    assert remediation_planner_manifest_fields(malformed) == {
        "planner_status": None,
        "rerun_trend": None,
        "next_best_command": None,
        "next_feedback_priority_reason": None,
        "planned_step_count": None,
    }
    assert remediation_execution_plan_manifest_fields(malformed) == {
        "execution_plan_status": None,
        "next_action_command": None,
        "next_action_feedback_priority_reason": None,
        "planned_action_count": None,
    }
    assert remediation_session_checkpoint_manifest_fields(malformed) == {
        "checkpoint_status": None,
        "next_action_command": None,
        "next_action_stage_signal_confidence": None,
        "next_action_feedback_priority_reason": None,
        "pending_action_count": None,
    }
    assert remediation_scoreboard_manifest_fields(malformed) == {
        "scoreboard_status": None,
        "next_action_command": None,
        "next_action_stage_signal_confidence": None,
        "next_action_feedback_priority_reason": None,
        "completion_rate": None,
    }


def test_remaining_remediation_manifest_field_selectors() -> None:
    assert remediation_session_manifest_fields(
        {
            "session_status": "ready_for_dry_run",
            "next_pending_command": "uv run sis monitoring-status",
            "next_pending_stage_signal_confidence": "low",
            "next_pending_feedback_priority_reason": "evaluation_failed",
            "pending_action_count": 2,
        }
    ) == {
        "session_status": "ready_for_dry_run",
        "next_pending_command": "uv run sis monitoring-status",
        "next_pending_stage_signal_confidence": "low",
        "next_pending_feedback_priority_reason": "evaluation_failed",
        "pending_action_count": 2,
    }
    assert remediation_evaluator_manifest_fields(
        {
            "evaluator_status": "failed",
            "next_action_key": "priority_2_check",
            "auto_fail_count": 1,
        }
    ) == {
        "evaluator_status": "failed",
        "next_action_key": "priority_2_check",
        "auto_fail_count": 1,
    }
    assert remediation_evidence_manifest_fields(
        {
            "evidence_status": "needs_manual_review",
            "next_manual_review_action_key": "priority_3_review",
            "manual_review_action_count": 4,
        }
    ) == {
        "evidence_status": "needs_manual_review",
        "next_manual_review_action_key": "priority_3_review",
        "manual_review_action_count": 4,
    }
    assert remediation_command_results_manifest_fields(
        {
            "command_results_status": "partial",
            "next_unobserved_action_key": "priority_4_observe",
            "missing_observation_count": 2,
        }
    ) == {
        "command_results_status": "partial",
        "next_unobserved_action_key": "priority_4_observe",
        "missing_observation_count": 2,
    }
