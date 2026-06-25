from __future__ import annotations

import pytest

from sis.backtest.compare_native_results import method_results, native_result


def test_native_result_requires_summary_object() -> None:
    with pytest.raises(ValueError, match="strategy backtest metrics missing summary object."):
        native_result({"summary": "not-a-dict"})


def test_native_result_defaults_malformed_nested_sections() -> None:
    result = native_result(
        {
            "strategy_id": "strategy-a",
            "schema_version": "strategy_backtest_metrics.v1",
            "summary": {
                "backtest_passed": False,
                "signals_considered": 8,
                "executed_count": 5,
                "blocked_count": 3,
                "aggregate_metrics": "not-a-dict",
                "executed_signal_summary": "not-a-dict",
                "capital": "not-a-dict",
            },
        }
    )

    assert result == {
        "engine_id": "strategy_authoring_native",
        "strategy_id": "strategy-a",
        "schema_version": "strategy_backtest_metrics.v1",
        "backtest_passed": False,
        "signals_considered": 8,
        "executed_count": 5,
        "blocked_count": 3,
        "trade_count": None,
        "total_return": None,
        "max_drawdown": None,
        "cost_drag_bps": None,
        "win_rate": None,
        "avg_signal_return": None,
        "total_notional_usd": None,
        "capital": {
            "initial_capital_usd": None,
            "net_pnl_usd": None,
            "ending_equity_usd": None,
            "max_drawdown_loss_usd": None,
        },
    }


def test_method_results_requires_summary_object() -> None:
    with pytest.raises(ValueError, match="strategy backtest metrics missing summary object."):
        method_results({"summary": None})


def test_method_results_normalizes_walk_forward_and_optimizer() -> None:
    results = method_results(
        {
            "summary": {
                "backtest_passed": True,
                "authoring_split_method": "walk_forward",
                "authoring_era_unit": "month",
                "signals_considered": 10,
                "executed_count": 6,
                "blocked_count": 4,
                "capital": {
                    "initial_capital_usd": 10000,
                    "net_pnl_usd": 300,
                    "ending_equity_usd": 10300,
                    "max_drawdown_loss_usd": 120,
                },
                "aggregate_metrics": {
                    "trade_count": 6,
                    "total_return": 0.03,
                    "max_drawdown": -0.012,
                    "cost_drag_bps": 3.4,
                    "stale_rejected_count": 1,
                    "halt_rejected_count": 0,
                },
                "walk_forward_eras": [
                    {
                        "era": "2026-01",
                        "signal_count": 4,
                        "executed_count": 3,
                        "capital": {"ending_equity_usd": 10150},
                        "aggregate_metrics": {"trade_count": 3, "total_return": 0.015},
                    },
                    "skip-me",
                ],
                "optimizer": {
                    "selection_metric": "total_return",
                    "selection_direction": "max",
                    "resolved_selection_direction": "max",
                    "variant_count": 2,
                    "best_variant": "not-a-dict",
                    "variants": [
                        "skip-me",
                        {
                            "variant_id": "variant-a",
                            "parameters": {"lookback": 20},
                            "backtest_passed": True,
                            "capital": {"ending_equity_usd": 10400},
                            "aggregate_metrics": {"trade_count": 7, "total_return": 0.04},
                        },
                    ],
                },
            }
        }
    )

    assert results[0] == {
        "method_id": "strategy_authoring_native_overall",
        "method_type": "native_overall",
        "engine_id": "strategy_authoring_native",
        "status": "available",
        "backtest_passed": True,
        "split_method": "walk_forward",
        "era_unit": "month",
        "signals_considered": 10,
        "executed_count": 6,
        "blocked_count": 4,
        "capital": {
            "initial_capital_usd": 10000,
            "net_pnl_usd": 300,
            "ending_equity_usd": 10300,
            "max_drawdown_loss_usd": 120,
        },
        "metrics": {
            "trade_count": 6,
            "total_return": 0.03,
            "max_drawdown": -0.012,
            "cost_drag_bps": 3.4,
            "stale_rejected_count": 1,
            "halt_rejected_count": 0,
        },
    }
    assert results[1] == {
        "method_id": "strategy_authoring_walk_forward",
        "method_type": "walk_forward",
        "engine_id": "strategy_authoring_native",
        "status": "available",
        "backtest_passed": True,
        "split_method": "walk_forward",
        "era_unit": "month",
        "era_count": 1,
        "eras": [
            {
                "era": "2026-01",
                "signal_count": 4,
                "executed_count": 3,
                "capital": {
                    "initial_capital_usd": None,
                    "net_pnl_usd": None,
                    "ending_equity_usd": 10150,
                    "max_drawdown_loss_usd": None,
                },
                "metrics": {
                    "trade_count": 3,
                    "total_return": 0.015,
                    "max_drawdown": None,
                    "cost_drag_bps": None,
                    "stale_rejected_count": None,
                    "halt_rejected_count": None,
                },
            }
        ],
        "metrics": {
            "trade_count": 6,
            "total_return": 0.03,
            "max_drawdown": -0.012,
            "cost_drag_bps": 3.4,
            "stale_rejected_count": 1,
            "halt_rejected_count": 0,
        },
    }
    assert results[2] == {
        "method_id": "strategy_authoring_optimizer_sweep",
        "method_type": "parameter_sweep",
        "engine_id": "strategy_authoring_native",
        "status": "available",
        "selection_metric": "total_return",
        "selection_direction": "max",
        "resolved_selection_direction": "max",
        "variant_count": 2,
        "best_variant": None,
        "variants": [
            {
                "variant_id": "variant-a",
                "parameters": {"lookback": 20},
                "backtest_passed": True,
                "capital": {
                    "initial_capital_usd": None,
                    "net_pnl_usd": None,
                    "ending_equity_usd": 10400,
                    "max_drawdown_loss_usd": None,
                },
                "metrics": {
                    "trade_count": 7,
                    "total_return": 0.04,
                    "max_drawdown": None,
                    "cost_drag_bps": None,
                    "stale_rejected_count": None,
                    "halt_rejected_count": None,
                },
            }
        ],
        "metrics": {
            "trade_count": 6,
            "total_return": 0.03,
            "max_drawdown": -0.012,
            "cost_drag_bps": 3.4,
            "stale_rejected_count": 1,
            "halt_rejected_count": 0,
        },
    }
