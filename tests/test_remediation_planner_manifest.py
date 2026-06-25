from __future__ import annotations

import json

from sis.reports.remediation_planner_manifest import latest_planner_manifest


def test_latest_planner_manifest_selects_last_matching_operation(tmp_path) -> None:
    operation_chain_path = tmp_path / "operation_chain.jsonl"
    operation_chain_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "operation": "remediation_planner_dry_run",
                        "run_id": "first",
                        "status": "regressed",
                    }
                ),
                json.dumps(
                    {
                        "operation": "other_operation",
                        "run_id": "ignored",
                        "status": "ok",
                    }
                ),
                json.dumps(
                    {
                        "operation": "remediation_planner_dry_run",
                        "run_id": "latest",
                        "status": "stalled",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert latest_planner_manifest(operation_chain_path) == {
        "operation": "remediation_planner_dry_run",
        "run_id": "latest",
        "status": "stalled",
    }


def test_latest_planner_manifest_handles_missing_path(tmp_path) -> None:
    assert latest_planner_manifest(None) == {}
    assert latest_planner_manifest(tmp_path / "missing.jsonl") == {}
