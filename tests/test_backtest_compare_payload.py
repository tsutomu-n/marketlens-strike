from __future__ import annotations

from sis.backtest.compare_payload import (
    comparison_diagnostics,
    completion_artifact,
    method_results,
    native_result,
    suite_results,
)


def test_compare_payload_helpers_normalize_representative_sections() -> None:
    metrics_payload = {
        "strategy_id": "strategy-a",
        "schema_version": "strategy_backtest_metrics.v1",
        "summary": {
            "backtest_passed": False,
            "signals_considered": 8,
            "executed_count": 5,
            "blocked_count": 3,
            "authoring_split_method": "walk_forward",
            "authoring_era_unit": "month",
            "aggregate_metrics": {
                "trade_count": 5,
                "total_return": -0.12,
                "max_drawdown": -0.2,
                "cost_drag_bps": 11.5,
            },
            "executed_signal_summary": {
                "win_rate": 0.4,
                "avg_signal_return": -0.01,
                "total_notional_usd": 12000,
            },
            "capital": {
                "initial_capital_usd": 10000,
                "net_pnl_usd": -1200,
                "ending_equity_usd": 8800,
                "max_drawdown_loss_usd": 2000,
            },
            "walk_forward_eras": [
                {
                    "era": "2026-01",
                    "signal_count": 3,
                    "executed_count": 2,
                    "aggregate_metrics": {"trade_count": 2, "total_return": -0.15},
                }
            ],
            "pass_thresholds": {
                "total_return": {"passed": False, "actual": -0.12, "threshold": 0.0},
                "trade_count": {"passed": True, "actual": 5, "threshold": 1},
            },
        },
    }
    suite_payload = {
        "suite_id": "suite-a",
        "runs": [
            {
                "run_id": "run-a",
                "case_id": "case-a",
                "strategy_id": "strategy-a",
                "method_id": "native",
                "backtest": {"split_method": "walk_forward"},
                "summary": {
                    "backtest_passed": False,
                    "aggregate_metrics": {"trade_count": 1, "total_return": -0.2},
                },
            }
        ],
        "best_run": {
            "run_id": "run-best",
            "case_id": "case-best",
            "strategy_id": "strategy-a",
            "method_id": "native",
            "summary": {
                "backtest_passed": True,
                "aggregate_metrics": {"trade_count": 2, "total_return": 0.04},
            },
        },
    }

    native = native_result(metrics_payload)
    methods = method_results(metrics_payload)
    suites = suite_results(suite_payload)
    diagnostics = comparison_diagnostics(
        metrics_payload=metrics_payload,
        method_results=methods,
        suite_results=suites,
    )
    completion = completion_artifact(
        {
            "schema_version": "strategy_backtest_data_availability.v1",
            "status": "complete",
            "summary": {"missing_count": 0},
            "permits_live_order": False,
            "wallet_used": False,
        }
    )

    assert native["engine_id"] == "strategy_authoring_native"
    assert native["capital"]["ending_equity_usd"] == 8800
    assert methods[1]["method_type"] == "walk_forward"
    assert methods[1]["eras"][0]["era"] == "2026-01"
    assert suites[0]["best_run"]["run_id"] == "run-best"
    assert suites[0]["runs"][0]["backtest_passed"] is False
    assert diagnostics["threshold_failures"] == [
        {"metric": "total_return", "actual": -0.12, "threshold": 0.0}
    ]
    assert "SUITE_FAILED_RUNS_PRESENT" in diagnostics["diagnostic_notes"]
    assert completion["status"] == "complete"
    assert completion["summary"] == {"missing_count": 0}
