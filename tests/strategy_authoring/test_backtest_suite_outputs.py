from __future__ import annotations

import json

from sis.research.strategy_lab.authoring.backtest_suite import (
    write_backtest_suite_outputs as suite_write_backtest_suite_outputs,
)
from sis.research.strategy_lab.authoring.backtest_suite_outputs import (
    write_backtest_suite_outputs,
)


def _suite_payload() -> dict[str, object]:
    return {
        "schema_version": "strategy_backtest_suite_result.v1",
        "suite_id": "suite_output_writer_test",
        "created_at": "2026-01-01T00:00:00+00:00",
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "selection": {
            "metric": "aggregate_metrics.total_return",
            "direction": "auto",
            "resolved_direction": "maximize",
        },
        "aggregate": {
            "run_count": 1,
            "strategy_count": 1,
            "case_count": 1,
            "passed_count": 1,
            "failed_count": 0,
            "trade_count": 4,
            "total_return": 0.08,
            "cost_drag_bps": 1.5,
        },
        "method_matrix": {
            "method_count": 1,
            "counts_by_method": {"walk_forward_day": 1},
            "counts_by_type": {"walk_forward": 1},
            "resampling": {"bootstrap": 1},
        },
        "best_run": {
            "run_id": "000-walk_forward_day",
            "case_id": "walk_forward_day",
            "method_id": "walk_forward_day",
            "strategy_id": "suite_strategy",
            "summary": {
                "aggregate_metrics": {
                    "trade_count": 4,
                    "total_return": 0.08,
                    "max_drawdown": -0.02,
                },
                "backtest_passed": True,
            },
        },
        "runs": [
            {
                "run_id": "000-walk_forward_day",
                "case_id": "walk_forward_day",
                "method_id": "walk_forward_day",
                "strategy_id": "suite_strategy",
                "summary": {
                    "aggregate_metrics": {
                        "trade_count": 4,
                        "total_return": 0.08,
                        "max_drawdown": -0.02,
                    },
                    "backtest_passed": True,
                },
            }
        ],
    }


def test_backtest_suite_outputs_module_writes_result_json_and_report(tmp_path) -> None:
    artifacts = write_backtest_suite_outputs(_suite_payload(), data_dir=tmp_path)

    assert artifacts == {
        "suite_result": tmp_path / "research/backtest_suite/strategy_backtest_suite_result.json",
        "suite_report": tmp_path / "reports/strategy_backtest_suite_report.md",
    }
    payload = json.loads(artifacts["suite_result"].read_text(encoding="utf-8"))
    assert payload["schema_version"] == "strategy_backtest_suite_result.v1"
    assert payload["suite_id"] == "suite_output_writer_test"
    assert payload["paper_only"] is True
    assert payload["permits_live_order"] is False
    assert payload["runs"][0]["case_id"] == "walk_forward_day"

    report = artifacts["suite_report"].read_text(encoding="utf-8")
    assert "# Strategy Backtest Suite Report" in report
    assert "paper_only: true" in report
    assert "- suite_id: suite_output_writer_test" in report
    assert "- run_count: 1" in report
    assert "- resolved_selection_direction: maximize" in report
    assert "- permits_live_order: False" in report
    assert "- wallet_used: False" in report
    assert "- exchange_write_used: False" in report
    assert (
        "| walk_forward_day | walk_forward_day | suite_strategy | 4 | 0.080000 | -0.02 | True |"
        in report
    )


def test_backtest_suite_keeps_output_writer_compatibility_import() -> None:
    assert suite_write_backtest_suite_outputs is write_backtest_suite_outputs
