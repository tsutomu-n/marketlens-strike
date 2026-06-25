from __future__ import annotations

from sis.reports.remediation_planner_diffs import (
    command_chain_diff,
    planner_entry_diffs,
    planner_rerun_diff,
    planner_status_rank,
)


def test_command_chain_diff_classifies_chain_changes() -> None:
    assert command_chain_diff([], ["a"])["trend"] == "first_run"
    assert command_chain_diff(["a"], ["a"])["trend"] == "unchanged"
    assert command_chain_diff(["a", "b"], ["a"])["trend"] == "narrowed"
    assert command_chain_diff(["a"], ["a", "b"])["trend"] == "expanded"
    assert command_chain_diff(["a", "b"], ["b", "c"]) == {
        "previous": ["a", "b"],
        "current": ["b", "c"],
        "added": ["c"],
        "removed": ["a"],
        "unchanged": ["b"],
        "trend": "changed",
    }


def test_planner_entry_diffs_classifies_added_removed_improved_and_regressed() -> None:
    previous = [
        {"source": "runbook", "reason": "strict", "status": "regressed", "commands": ["a"]},
        {"source": "phase", "reason": "old", "status": "planned", "commands": ["old"]},
        {"source": "phase", "reason": "worse", "status": "matched", "commands": ["w"]},
    ]
    current = [
        {"source": "runbook", "reason": "strict", "status": "stalled", "commands": ["a"]},
        {"source": "phase", "reason": "new", "status": "planned", "commands": ["new"]},
        {"source": "phase", "reason": "worse", "status": "regressed", "commands": ["w"]},
    ]

    diffs = planner_entry_diffs(previous, current)

    assert diffs["runbook:strict"]["trend"] == "improved"
    assert diffs["phase:old"]["trend"] == "removed"
    assert diffs["phase:new"]["trend"] == "new"
    assert diffs["phase:worse"]["trend"] == "regressed"


def test_planner_rerun_diff_preserves_manifest_note_fallbacks_and_trends() -> None:
    first = planner_rerun_diff(
        {},
        {},
        planner_status="planned",
        planned_step_count=2,
        next_best_command="uv run sis validate-artifacts",
        recommended_command_chain=["uv run sis validate-artifacts"],
    )
    assert first["trend"] == "first_run"
    assert first["command_chain_diff"]["trend"] == "first_run"

    previous_manifest = {
        "run_id": "run-1",
        "status": "regressed",
        "notes": [
            "planned_step_count=3",
            "next_best_command=uv run sis refresh-operations-artifacts",
        ],
    }

    manifest_only_diff = planner_rerun_diff(
        {},
        previous_manifest,
        planner_status="stalled",
        planned_step_count=2,
        next_best_command="uv run sis validate-artifacts",
        recommended_command_chain=[
            "uv run sis validate-artifacts",
            "uv run sis refresh-operations-artifacts",
        ],
    )

    assert manifest_only_diff["previous_manifest_status"] == "regressed"
    assert (
        manifest_only_diff["previous_next_best_command"]
        == "uv run sis refresh-operations-artifacts"
    )
    assert manifest_only_diff["previous_planned_step_count"] == 3
    assert manifest_only_diff["previous_manifest_run_id"] == "run-1"
    assert manifest_only_diff["trend"] == "improved"
    assert manifest_only_diff["command_chain_diff"]["trend"] == "first_run"

    diff = planner_rerun_diff(
        {
            "recommended_command_chain": [
                "uv run sis refresh-operations-artifacts",
                "uv run sis compare-operations-artifacts",
            ],
        },
        previous_manifest,
        planner_status="stalled",
        planned_step_count=2,
        next_best_command="uv run sis validate-artifacts",
        recommended_command_chain=[
            "uv run sis validate-artifacts",
            "uv run sis refresh-operations-artifacts",
        ],
    )
    assert diff["command_chain_diff"]["trend"] == "changed"
    assert planner_status_rank("matched") < planner_status_rank("regressed")
