from __future__ import annotations

from sis.backtest.compare_diagnostics import comparison_diagnostics


def test_comparison_diagnostics_reports_thresholds_weakest_eras_and_suite_runs() -> None:
    diagnostics = comparison_diagnostics(
        metrics_payload={
            "summary": {
                "pass_thresholds": {
                    "bool_metric": {"passed": False, "actual": True, "threshold": False},
                    "drawdown": {"passed": False, "actual": -0.2, "threshold": -0.1},
                    "ignored_pass": {"passed": True, "actual": 1, "threshold": 0},
                }
            }
        },
        method_results=[
            {
                "method_id": "walk_forward",
                "eras": [
                    {
                        "era": "2026-W02",
                        "metrics": {
                            "trade_count": 2,
                            "total_return": 0.03,
                            "max_drawdown": -0.01,
                            "cost_drag_bps": 1.0,
                        },
                    },
                    {
                        "era": "2026-W01",
                        "metrics": {
                            "trade_count": 1,
                            "total_return": -0.04,
                            "max_drawdown": -0.03,
                            "cost_drag_bps": 2.0,
                        },
                    },
                ],
            }
        ],
        suite_results=[
            {
                "suite_id": "suite-a",
                "best_run": {
                    "run_id": "run-best",
                    "case_id": "case-best",
                    "method_id": "method-a",
                    "strategy_id": "strategy-a",
                    "backtest_passed": True,
                    "metrics": {
                        "trade_count": 4,
                        "total_return": 0.05,
                        "max_drawdown": -0.02,
                        "cost_drag_bps": 3.0,
                    },
                },
                "runs": [
                    {
                        "run_id": "run-fail",
                        "case_id": "case-fail",
                        "strategy_id": "strategy-a",
                        "backtest_passed": False,
                        "metrics": {
                            "trade_count": 0,
                            "total_return": -0.08,
                            "max_drawdown": -0.06,
                            "cost_drag_bps": 4.0,
                        },
                    }
                ],
            }
        ],
    )

    assert diagnostics["threshold_failures"] == [
        {"metric": "bool_metric", "actual": None, "threshold": None},
        {"metric": "drawdown", "actual": -0.2, "threshold": -0.1},
    ]
    assert diagnostics["weakest_eras"] == [
        {
            "method_id": "walk_forward",
            "era": "2026-W01",
            "trade_count": 1,
            "total_return": -0.04,
            "max_drawdown": -0.03,
            "cost_drag_bps": 2.0,
        },
        {
            "method_id": "walk_forward",
            "era": "2026-W02",
            "trade_count": 2,
            "total_return": 0.03,
            "max_drawdown": -0.01,
            "cost_drag_bps": 1.0,
        },
    ]
    assert diagnostics["suite_best_runs"] == [
        {
            "suite_id": "suite-a",
            "run_id": "run-best",
            "case_id": "case-best",
            "method_id": "method-a",
            "strategy_id": "strategy-a",
            "backtest_passed": True,
            "trade_count": 4,
            "total_return": 0.05,
            "max_drawdown": -0.02,
            "cost_drag_bps": 3.0,
        }
    ]
    assert diagnostics["suite_failed_runs"] == [
        {
            "suite_id": "suite-a",
            "run_id": "run-fail",
            "case_id": "case-fail",
            "strategy_id": "strategy-a",
            "trade_count": 0,
            "total_return": -0.08,
            "max_drawdown": -0.06,
            "cost_drag_bps": 4.0,
        }
    ]
    assert diagnostics["diagnostic_notes"] == [
        "THRESHOLD_FAILURES_PRESENT",
        "WEAKEST_ERAS_AVAILABLE",
        "SUITE_BEST_RUN_AVAILABLE",
        "SUITE_FAILED_RUNS_PRESENT",
    ]


def test_comparison_diagnostics_reports_no_findings_note() -> None:
    assert comparison_diagnostics(
        metrics_payload={"summary": {}},
        method_results=[],
        suite_results=[],
    ) == {
        "threshold_failures": [],
        "weakest_eras": [],
        "suite_best_runs": [],
        "suite_failed_runs": [],
        "diagnostic_notes": ["NO_DIAGNOSTIC_FINDINGS"],
    }
