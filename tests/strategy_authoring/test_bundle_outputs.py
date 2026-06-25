from __future__ import annotations

import json

from sis.research.strategy_lab.authoring.bundle import (
    write_authoring_bundle_outputs as bundle_write_authoring_bundle_outputs,
)
from sis.research.strategy_lab.authoring.bundle_outputs import (
    write_authoring_bundle_outputs,
)


def _bundle_payload() -> dict[str, object]:
    group_metrics = {
        "group_count": 1,
        "complete_group_count": 1,
        "incomplete_group_count": 0,
        "expected_leg_count": 2,
        "executed_leg_count": 2,
        "weighted_total_return": 0.024,
        "total_notional_usd": 1500.0,
        "weighted_notional_return": 0.018,
        "weighted_cost_drag_bps": 0.9,
        "weighted_win_rate": 0.6,
        "worst_group_return": -0.01,
        "weighted_max_drawdown": -0.012,
        "weighted_profit_factor": 1.8,
        "weighted_avg_leg_return_imbalance": 0.0012,
    }
    member_group_metrics = {
        "group_count": 1,
        "complete_group_count": 1,
        "total_return": 0.03,
        "notional_weighted_total_return": 0.0225,
        "total_notional_usd": 1500.0,
        "win_rate": 0.75,
        "max_drawdown": -0.015,
        "profit_factor": 2.25,
        "avg_leg_return_imbalance": 0.0015,
    }
    return {
        "schema_version": "strategy_authoring_bundle_result.v1",
        "bundle_id": "bundle_output_writer_test",
        "paper_only": True,
        "live_order_submitted": False,
        "portfolio": {
            "selection_metric": "aggregate_metrics.total_return",
            "selection_direction": "auto",
            "resolved_selection_direction": "maximize",
        },
        "aggregate_metrics": {
            "member_count": 1,
            "weighted_total_return": 0.024,
            "multi_leg_group_metrics": group_metrics,
        },
        "best_member": {"strategy_id": "bundle_member_a"},
        "members": [
            {
                "strategy_id": "bundle_member_a",
                "effective_allocation_weight": 0.8,
                "summary": {
                    "aggregate_metrics": {
                        "trade_count": 5,
                        "total_return": 0.03,
                    },
                    "backtest_passed": True,
                    "multi_leg_group_metrics": member_group_metrics,
                },
            }
        ],
    }


def test_bundle_outputs_module_writes_result_json_and_report(tmp_path) -> None:
    artifacts = write_authoring_bundle_outputs(_bundle_payload(), data_dir=tmp_path)

    assert artifacts == {
        "bundle_result": tmp_path / "research/strategy_authoring_bundle_result.json",
        "bundle_report": tmp_path / "reports/strategy_authoring_bundle_report.md",
    }
    payload = json.loads(artifacts["bundle_result"].read_text(encoding="utf-8"))
    assert payload["schema_version"] == "strategy_authoring_bundle_result.v1"
    assert payload["bundle_id"] == "bundle_output_writer_test"
    assert payload["paper_only"] is True
    assert payload["live_order_submitted"] is False
    assert payload["members"][0]["strategy_id"] == "bundle_member_a"

    report = artifacts["bundle_report"].read_text(encoding="utf-8")
    assert "# Strategy Authoring Bundle Report" in report
    assert "paper_only: true" in report
    assert "- bundle_id: bundle_output_writer_test" in report
    assert "- member_count: 1" in report
    assert "- weighted_total_return: 0.024000" in report
    assert "- best_member: bundle_member_a" in report
    assert "| bundle_member_a | 0.8000 | 5 | 0.030000 | True |" in report
    assert "## Multi-Leg Group Metrics" in report
    assert "- group_count: 1" in report
    assert "- weighted_notional_return: 0.018000" in report
    assert "- weighted_profit_factor: 1.800000" in report
    assert (
        "| bundle_member_a | 1 | 1 | 1.000000 | 0.024000 | 0.018000 | 1500.000000 | 0.600000 | -0.012000 | 1.800000 | 0.001200 |"
        in report
    )


def test_bundle_keeps_output_writer_compatibility_import() -> None:
    assert bundle_write_authoring_bundle_outputs is write_authoring_bundle_outputs
