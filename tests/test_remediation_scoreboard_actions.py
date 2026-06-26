from __future__ import annotations

from sis.reports.remediation_scoreboard_actions import (
    action_observed_sources,
    action_priority_key,
    as_int,
    enrich_actions_with_feedback,
    feedback_priority_reason,
    next_action,
    observed_source_counts,
    scoreboard_status,
)


def test_as_int_preserves_existing_coercion_rules() -> None:
    assert as_int(True) is None
    assert as_int(4) == 4
    assert as_int(4.9) == 4
    assert as_int(" 7 ") == 7
    assert as_int("") is None
    assert as_int("bad") is None


def test_action_observed_sources_filters_non_strings() -> None:
    assert action_observed_sources({"observed_sources": ["cli", 1, "report", None]}) == [
        "cli",
        "report",
    ]
    assert action_observed_sources({"observed_sources": "cli"}) == []


def test_action_priority_key_prefers_effective_priority_then_priority() -> None:
    high_priority = {
        "effective_priority": "1",
        "priority": "9",
        "stage": "execute",
        "stage_signal_confidence": "high",
        "sequence": "2",
        "action_key": "b",
    }
    lower_priority = {
        "priority": "2",
        "stage": "preflight",
        "stage_signal_confidence": "low",
        "sequence": "1",
        "action_key": "a",
    }

    assert action_priority_key(high_priority) < action_priority_key(lower_priority)


def test_observed_source_counts_counts_sources_across_actions() -> None:
    assert observed_source_counts(
        [
            {"observed_sources": ["cli", "report"]},
            {"observed_sources": ["cli", 4]},
            {"observed_sources": None},
        ]
    ) == {"cli": 2, "report": 1}


def test_feedback_priority_reason_matches_existing_order() -> None:
    assert feedback_priority_reason("fail", "observed") == "evaluation_failed"
    assert feedback_priority_reason("manual_review", "observed") == "manual_review_pending"
    assert feedback_priority_reason("partial", "observed") == "partial_verification"
    assert feedback_priority_reason(None, "missing") == "missing_command_observation"
    assert feedback_priority_reason("pass", "observed") == "verification_passed"
    assert feedback_priority_reason(None, "observed") == "no_feedback"


def test_enrich_actions_with_feedback_adds_feedback_fields() -> None:
    actions = [{"action_key": "a", "checkpoint_status": "pending"}]

    assert enrich_actions_with_feedback(
        actions,
        {"a": "observed"},
        {"a": "manual_review"},
    ) == [
        {
            "action_key": "a",
            "checkpoint_status": "pending",
            "feedback_observation_status": "observed",
            "feedback_evaluation_result": "manual_review",
            "feedback_priority_reason": "manual_review_pending",
        }
    ]


def test_next_action_prefers_retry_then_feedback_then_action_priority() -> None:
    actions = [
        {
            "action_key": "pending-fail",
            "command": "pending",
            "checkpoint_status": "pending",
            "feedback_priority_reason": "evaluation_failed",
            "priority": 1,
        },
        {
            "action_key": "retry-pass",
            "command": "retry pass",
            "checkpoint_status": "retry",
            "feedback_priority_reason": "verification_passed",
            "priority": 1,
        },
        {
            "action_key": "retry-fail",
            "command": "retry fail",
            "checkpoint_status": "retry",
            "feedback_priority_reason": "evaluation_failed",
            "priority": 9,
        },
    ]

    assert next_action(actions) == actions[2]


def test_scoreboard_status_classifies_summary_counts() -> None:
    actions = [{"action_key": "a"}, {"action_key": "b"}]

    assert scoreboard_status({}, []) == "no_actions"
    assert scoreboard_status({"fail_action_count": 1}, actions) == "blocked"
    assert scoreboard_status({"retry_action_count": 1}, actions) == "retrying"
    assert scoreboard_status({"pending_action_count": 1}, actions) == "in_progress"
    assert scoreboard_status({"pass_action_count": 2}, actions) == "completed"
    assert scoreboard_status({"pass_action_count": 1}, actions) == "in_progress"
