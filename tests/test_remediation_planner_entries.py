from __future__ import annotations

from sis.reports.remediation_planner_entries import (
    entry_key,
    evaluator_provenance_map,
    feedback_maps,
    feedback_priority_rank,
    planner_status,
    planner_entries,
    recommended_command_chain,
    source_reason_key,
)


def test_evaluator_provenance_map_flattens_nested_observed_sources() -> None:
    provenance = evaluator_provenance_map(
        {
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_preflight_1",
                    "source": "paper_operations_runbook",
                    "reason": "strict_validation_failed",
                    "signal_evaluations": [
                        {
                            "signal": "validate-artifacts",
                            "observed_source": {
                                "primary": "stdout_stderr",
                                "fallbacks": ["manifest_notes", "markdown_reports"],
                            },
                        }
                    ],
                }
            ]
        }
    )

    key = source_reason_key("paper_operations_runbook", "strict_validation_failed")
    assert provenance[key]["supporting_action_keys"] == [
        "priority_2_paper_operations_runbook_strict_preflight_1"
    ]
    assert provenance[key]["observed_sources"] == [
        "stdout_stderr",
        "manifest_notes",
        "markdown_reports",
    ]
    assert provenance[key]["signal_observed_sources"] == {
        "validate-artifacts": {
            "primary": "stdout_stderr",
            "fallbacks": ["manifest_notes", "markdown_reports"],
        }
    }


def test_feedback_maps_and_planner_entries_prioritize_failed_direct_feedback() -> None:
    observation_status_by_action, evaluation_result_by_action = feedback_maps(
        {
            "entries": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_preflight_1",
                    "observation_status": "observed",
                }
            ],
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_preflight_1",
                    "evaluation_result": "fail",
                }
            ],
        }
    )
    provenance = {
        source_reason_key("paper_operations_runbook", "strict_validation_failed"): {
            "observed_sources": ["stdout_stderr"],
            "signal_observed_sources": {"validate-artifacts": "stdout_stderr"},
            "supporting_action_keys": ["priority_2_paper_operations_runbook_strict_preflight_1"],
        }
    }

    entries = planner_entries(
        {
            "remediation_order": [
                {"priority": 2, "reason": "strict_validation_failed"},
            ],
            "remediation_recommendations": {
                "strict_validation_failed": {
                    "status": "stalled",
                    "why": "signals did not move toward target",
                    "commands": ["uv run sis validate-artifacts --strict"],
                }
            },
        },
        source="paper_operations_runbook",
        provenance_map=provenance,
        observation_status_by_action=observation_status_by_action,
        evaluation_result_by_action=evaluation_result_by_action,
    )

    assert entry_key(entries[0]) == "paper_operations_runbook:strict_validation_failed"
    assert entries[0]["source_confidence"] == "high"
    assert entries[0]["source_policy"] == "direct_observation_priority"
    assert entries[0]["feedback_priority_reason"] == "evaluation_failed"
    assert entries[0]["effective_priority"] == -1
    assert entries[0]["commands"] == ["uv run sis validate-artifacts --strict"]
    assert entries[0]["feedback_evaluation_results"] == {
        "priority_2_paper_operations_runbook_strict_preflight_1": "fail"
    }
    assert feedback_priority_rank("evaluation_failed") < feedback_priority_rank(
        "manual_review_pending"
    )


def test_recommended_command_chain_preserves_first_seen_unique_string_commands() -> None:
    entries = [
        {"commands": ["uv run sis first", 123, "uv run sis second"]},
        {"commands": ["uv run sis first", "uv run sis third"]},
        {"commands": "uv run sis ignored"},
    ]

    assert recommended_command_chain(entries) == [
        "uv run sis first",
        "uv run sis second",
        "uv run sis third",
    ]


def test_planner_status_preserves_precedence() -> None:
    assert planner_status([]) == "no_actions"
    assert planner_status([{"status": "matched"}]) == "matched"
    assert planner_status([{"status": "planned"}, {"status": "unknown"}]) == "planned"
    assert planner_status([{"status": "improving"}, {"status": "matched"}]) == "improving"
    assert planner_status([{"status": "stalled"}, {"status": "improving"}]) == "stalled"
    assert planner_status([{"status": "regressed"}, {"status": "stalled"}]) == "regressed"
