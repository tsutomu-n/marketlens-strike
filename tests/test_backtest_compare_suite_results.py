from __future__ import annotations

from sis.backtest.compare_suite_results import suite_results


def test_suite_results_returns_empty_list_for_missing_payload() -> None:
    assert suite_results(None) == []


def test_suite_results_normalizes_best_run_runs_and_boundaries() -> None:
    payload = {
        "suite_id": "suite-a",
        "schema_version": "strategy_backtest_suite.v1",
        "selection": {"metric": "total_return"},
        "aggregate": {"run_count": 3},
        "method_matrix": {"method_count": 2},
        "best_run": {
            "run_id": "run-best",
            "case_id": "case-best",
            "strategy_id": "strategy-a",
            "signal_count": 11,
            "source_signal_count": 13,
            "evaluation_signal_count": 7,
            "method_id": "walk_forward_240m",
            "method_type": "walk_forward",
            "base_method_id": "native",
            "resampling": {"interval": "240m"},
            "backtest": {
                "split_method": "walk_forward",
                "era_unit": "month",
                "label_horizon_minutes": 240,
                "initial_capital_usd": 10000,
                "evaluation_start_at": "2026-01-01T00:00:00Z",
                "evaluation_end_at": "2026-01-31T23:59:00Z",
            },
            "summary": {
                "backtest_passed": True,
                "capital": {
                    "initial_capital_usd": 10000,
                    "net_pnl_usd": 450,
                    "ending_equity_usd": 10450,
                    "max_drawdown_loss_usd": 210,
                },
                "aggregate_metrics": {
                    "trade_count": 5,
                    "total_return": 0.045,
                    "max_drawdown": -0.021,
                    "cost_drag_bps": 4.2,
                    "stale_rejected_count": 1,
                    "halt_rejected_count": 0,
                },
            },
        },
        "runs": [
            "skip-me",
            {
                "run_id": "run-a",
                "case_id": "case-a",
                "strategy_id": "strategy-a",
                "method_id": "native",
                "resampling": "not-a-dict",
                "backtest": "not-a-dict",
                "summary": "not-a-dict",
            },
        ],
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }

    normalized = suite_results(payload)

    assert normalized == [
        {
            "suite_id": "suite-a",
            "schema_version": "strategy_backtest_suite.v1",
            "selection": {"metric": "total_return"},
            "aggregate": {"run_count": 3},
            "method_matrix": {"method_count": 2},
            "best_run": {
                "run_id": "run-best",
                "case_id": "case-best",
                "strategy_id": "strategy-a",
                "signal_count": 11,
                "source_signal_count": 13,
                "evaluation_signal_count": 7,
                "method_id": "walk_forward_240m",
                "method_type": "walk_forward",
                "base_method_id": "native",
                "resampling": {"interval": "240m"},
                "backtest_passed": True,
                "split_method": "walk_forward",
                "era_unit": "month",
                "label_horizon_minutes": 240,
                "initial_capital_usd": 10000,
                "evaluation_start_at": "2026-01-01T00:00:00Z",
                "evaluation_end_at": "2026-01-31T23:59:00Z",
                "capital": {
                    "initial_capital_usd": 10000,
                    "net_pnl_usd": 450,
                    "ending_equity_usd": 10450,
                    "max_drawdown_loss_usd": 210,
                },
                "metrics": {
                    "trade_count": 5,
                    "total_return": 0.045,
                    "max_drawdown": -0.021,
                    "cost_drag_bps": 4.2,
                    "stale_rejected_count": 1,
                    "halt_rejected_count": 0,
                },
            },
            "runs": [
                {
                    "run_id": "run-a",
                    "case_id": "case-a",
                    "strategy_id": "strategy-a",
                    "signal_count": None,
                    "source_signal_count": None,
                    "evaluation_signal_count": None,
                    "method_id": "native",
                    "method_type": None,
                    "base_method_id": None,
                    "resampling": None,
                    "backtest_passed": None,
                    "split_method": None,
                    "era_unit": None,
                    "label_horizon_minutes": None,
                    "initial_capital_usd": None,
                    "evaluation_start_at": None,
                    "evaluation_end_at": None,
                    "capital": {
                        "initial_capital_usd": None,
                        "net_pnl_usd": None,
                        "ending_equity_usd": None,
                        "max_drawdown_loss_usd": None,
                    },
                    "metrics": {
                        "trade_count": None,
                        "total_return": None,
                        "max_drawdown": None,
                        "cost_drag_bps": None,
                        "stale_rejected_count": None,
                        "halt_rejected_count": None,
                    },
                }
            ],
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ]


def test_suite_results_defaults_optional_sections_to_empty_objects() -> None:
    normalized = suite_results({"suite_id": "suite-a", "runs": [], "best_run": "not-a-dict"})

    assert normalized == [
        {
            "suite_id": "suite-a",
            "schema_version": None,
            "selection": {},
            "aggregate": {},
            "method_matrix": {},
            "best_run": None,
            "runs": [],
            "permits_live_order": None,
            "live_conversion_allowed": None,
            "wallet_used": None,
            "exchange_write_used": None,
        }
    ]
