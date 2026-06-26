from __future__ import annotations

import json
from pathlib import Path

from sis.reports.phase_gate_review_pr12 import (
    pr12_fresh_read_only_smoke_completed,
    pr12_fresh_read_only_smoke_next_actions,
)


def test_pr12_fresh_read_only_smoke_completed_requires_go_one_hour_and_no_next_action() -> None:
    assert pr12_fresh_read_only_smoke_completed(
        {
            "final_decision": "READ_ONLY_GO",
            "observed_window_seconds": 3600,
            "next_action": "none",
        }
    )
    assert pr12_fresh_read_only_smoke_completed(
        {
            "final_decision": "READ_ONLY_GO",
            "observed_window_seconds": 3600.5,
            "next_action": "none",
        }
    )
    assert not pr12_fresh_read_only_smoke_completed(
        {
            "final_decision": "NO_GO",
            "observed_window_seconds": 3600,
            "next_action": "none",
        }
    )
    assert not pr12_fresh_read_only_smoke_completed(
        {
            "final_decision": "READ_ONLY_GO",
            "observed_window_seconds": 3599.9,
            "next_action": "none",
        }
    )
    assert not pr12_fresh_read_only_smoke_completed(
        {
            "final_decision": "READ_ONLY_GO",
            "observed_window_seconds": True,
            "next_action": "none",
        }
    )
    assert not pr12_fresh_read_only_smoke_completed(
        {
            "final_decision": "READ_ONLY_GO",
            "observed_window_seconds": 3600,
            "next_action": "rerun",
        }
    )


def test_pr12_fresh_read_only_smoke_next_actions_reads_summary(tmp_path: Path) -> None:
    summary_path = tmp_path / "ops/pr12_fresh_read_only_smoke_summary.json"
    summary_path.parent.mkdir(parents=True)
    summary_path.write_text(
        json.dumps(
            {
                "final_decision": "READ_ONLY_GO",
                "observed_window_seconds": 3600,
                "next_action": "none",
            }
        ),
        encoding="utf-8",
    )

    assert pr12_fresh_read_only_smoke_next_actions(tmp_path) == []

    summary_path.write_text(
        json.dumps(
            {
                "final_decision": "READ_ONLY_GO",
                "observed_window_seconds": 1200,
                "next_action": "none",
            }
        ),
        encoding="utf-8",
    )

    assert pr12_fresh_read_only_smoke_next_actions(tmp_path) == ["run_pr12_fresh_read_only_smoke"]


def test_pr12_fresh_read_only_smoke_next_actions_requires_summary(tmp_path: Path) -> None:
    assert pr12_fresh_read_only_smoke_next_actions(tmp_path) == ["run_pr12_fresh_read_only_smoke"]
