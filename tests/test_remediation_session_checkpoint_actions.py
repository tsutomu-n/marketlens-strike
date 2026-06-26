from __future__ import annotations

from sis.reports.remediation_session_checkpoint_actions import (
    action_observed_sources,
    checkpoint_summary_status,
    enrich_actions_with_feedback,
    merge_actions,
    next_action,
    observed_source_counts,
)


def test_action_observed_sources_and_counts_ignore_non_strings() -> None:
    assert action_observed_sources({"observed_sources": ["stdout", 1, "report"]}) == [
        "stdout",
        "report",
    ]
    assert action_observed_sources({"observed_sources": "stdout"}) == []
    assert observed_source_counts(
        [
            {"observed_sources": ["stdout", "report"]},
            {"observed_sources": ["stdout"]},
            "ignored",
        ]
    ) == {"stdout": 2, "report": 1}


def test_merge_actions_preserves_previous_state_and_records_current_update() -> None:
    merged = merge_actions(
        [
            {
                "action_key": "a1",
                "command": "uv run sis validate-artifacts --strict",
                "priority": 2,
                "suggested_result": "pass",
            }
        ],
        [
            {
                "action_key": "a1",
                "checkpoint_status": "pending",
                "operator_notes": ["first note"],
                "evidence_paths": ["data/ops/old.log"],
                "observed_signals": ["old signal"],
            }
        ],
        action_key="a1",
        result="retry",
        note="still failing",
        evidence_path="data/ops/new.log",
        observed_signal="new signal",
        stdout_summary="issues=1",
        stderr_summary="",
        exit_code=1,
    )

    assert merged == [
        {
            "action_key": "a1",
            "command": "uv run sis validate-artifacts --strict",
            "priority": 2,
            "suggested_result": "pass",
            "checkpoint_status": "retry",
            "evidence_status": "needs_review",
            "operator_notes": ["first note", "still failing"],
            "evidence_paths": ["data/ops/old.log", "data/ops/new.log"],
            "observed_signals": ["old signal", "new signal"],
            "latest_exit_code": 1,
            "latest_stdout_summary": "issues=1",
            "latest_stderr_summary": None,
            "command_result_records": [
                {
                    "evidence_path": "data/ops/new.log",
                    "observed_signal": "new signal",
                    "stdout_summary": "issues=1",
                    "exit_code": 1,
                    "checkpoint_result": "retry",
                }
            ],
        }
    ]


def test_enrich_actions_and_next_action_prioritize_retry_failed_feedback() -> None:
    actions = enrich_actions_with_feedback(
        [
            {
                "action_key": "retry_action",
                "command": "uv run sis phase-gate-review",
                "checkpoint_status": "retry",
                "priority": 5,
                "stage": "post_check",
                "stage_signal_confidence": "high",
                "sequence": 2,
            },
            {
                "action_key": "pending_action",
                "command": "uv run sis implementation-status",
                "checkpoint_status": "pending",
                "priority": 1,
                "stage": "preflight",
                "stage_signal_confidence": "low",
                "sequence": 1,
            },
        ],
        {"retry_action": "observed", "pending_action": "observed"},
        {"retry_action": "fail", "pending_action": "pass"},
    )

    assert actions[0]["feedback_priority_reason"] == "evaluation_failed"
    assert actions[1]["feedback_priority_reason"] == "verification_passed"
    assert next_action(actions) == actions[0]


def test_checkpoint_summary_status() -> None:
    assert checkpoint_summary_status([]) == "no_actions"
    assert checkpoint_summary_status([{"checkpoint_status": "pass"}]) == "completed"
    assert checkpoint_summary_status([{"checkpoint_status": "fail"}]) == "attention_required"
    assert checkpoint_summary_status([{"checkpoint_status": "retry"}]) == "retry_pending"
    assert (
        checkpoint_summary_status([{"checkpoint_status": "pass"}, {"checkpoint_status": "pending"}])
        == "in_progress"
    )
