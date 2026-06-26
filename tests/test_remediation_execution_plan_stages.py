from __future__ import annotations

from sis.reports.remediation_execution_plan_stages import (
    execution_plan_status,
    feedback_priority_rank,
    stage_order,
)


def test_stage_order_uses_post_check_only_for_matched_entries() -> None:
    assert stage_order(
        "matched",
        "unchanged",
        "high",
        feedback_priority_reason="verification_passed",
        execute_signal_confidence="high",
        postcheck_signal_confidence="high",
    ) == ["post_check"]


def test_stage_order_requires_full_cycle_for_weak_or_regressed_signals() -> None:
    assert stage_order(
        "stalled",
        "unchanged",
        "high",
        feedback_priority_reason="verification_passed",
        execute_signal_confidence="low",
        postcheck_signal_confidence="high",
    ) == ["preflight", "execute", "post_check"]
    assert stage_order(
        "ok",
        "regressed",
        "high",
        feedback_priority_reason="verification_passed",
        execute_signal_confidence="high",
        postcheck_signal_confidence="high",
    ) == ["preflight", "execute", "post_check"]
    assert stage_order(
        "ok",
        "unchanged",
        "unknown",
        feedback_priority_reason="manual_review_pending",
        execute_signal_confidence="high",
        postcheck_signal_confidence="high",
    ) == ["preflight", "execute", "post_check"]


def test_stage_order_uses_execute_then_post_check_for_improving_or_default_entries() -> None:
    assert stage_order(
        "improving",
        "improved",
        "high",
        feedback_priority_reason="verification_passed",
        execute_signal_confidence="high",
        postcheck_signal_confidence="high",
    ) == ["execute", "post_check"]
    assert stage_order(
        "planned",
        "unchanged",
        "high",
        feedback_priority_reason="verification_passed",
        execute_signal_confidence="high",
        postcheck_signal_confidence="high",
    ) == ["execute", "post_check"]


def test_execution_plan_status_prioritizes_worst_entry_status() -> None:
    assert execution_plan_status([]) == "no_actions"
    assert execution_plan_status([{"recommendation_status": "matched"}]) == "postcheck_only"
    assert execution_plan_status([{"recommendation_status": "improving"}]) == "in_progress"
    assert execution_plan_status([{"recommendation_status": "stalled"}]) == "stalled"
    assert execution_plan_status([{"recommendation_status": "regressed"}]) == "regressed"
    assert execution_plan_status([{"recommendation_status": "unknown"}]) == "planned"


def test_feedback_priority_rank_keeps_existing_sort_order() -> None:
    reasons = [
        "no_feedback",
        "verification_passed",
        "missing_command_observation",
        "partial_verification",
        "manual_review_pending",
        "evaluation_failed",
        None,
    ]

    assert sorted(reasons, key=feedback_priority_rank) == [
        "evaluation_failed",
        "manual_review_pending",
        "partial_verification",
        "missing_command_observation",
        "verification_passed",
        "no_feedback",
        None,
    ]
