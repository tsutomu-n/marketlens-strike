from __future__ import annotations

from sis.backtest.compare_report import write_strategy_backtest_comparison_report


def test_write_strategy_backtest_comparison_report_writes_core_sections(tmp_path) -> None:
    path = tmp_path / "reports/strategy_backtest_comparison_report.md"
    payload = {
        "comparison_id": "sha256:demo",
        "source_metrics_path": "data/research/strategy_backtest_metrics.json",
        "native_result": {
            "engine_id": "strategy_authoring_native",
            "strategy_id": "demo_strategy",
            "backtest_passed": True,
            "trade_count": 2,
            "total_return": 0.03,
            "max_drawdown": -0.01,
            "cost_drag_bps": 1.5,
            "capital": {
                "initial_capital_usd": 1000.0,
                "net_pnl_usd": 30.0,
                "ending_equity_usd": 1030.0,
                "max_drawdown_loss_usd": 10.0,
            },
        },
        "method_results": [
            {
                "method_id": "strategy_authoring_native_overall",
                "method_type": "native_overall",
                "status": "available",
                "metrics": {
                    "trade_count": 2,
                    "total_return": 0.03,
                    "max_drawdown": -0.01,
                },
            }
        ],
        "suite_results": [],
        "comparison_diagnostics": {
            "threshold_failures": [],
            "weakest_eras": [],
            "suite_best_runs": [],
        },
        "adapter_spike": None,
        "framework_run": None,
        "external_results": [],
        "portfolio_comparison": None,
        "metric_extension": None,
        "report_extension": None,
        "stress": None,
        "regime_split": None,
        "rolling_stability": None,
        "benchmark_relative": None,
        "framework_adapters": [
            {
                "framework_id": "vectorbt",
                "status": "not_installed",
                "version": None,
                "adapter_role": "candidate",
                "adoption_note": "not installed",
            }
        ],
    }

    result = write_strategy_backtest_comparison_report(path, payload)

    assert result == path
    text = path.read_text(encoding="utf-8")
    assert "# Strategy Backtest Comparison" in text
    assert "strategy_authoring_native_overall" in text
    assert "## Framework Adapter Status" in text
    assert "This comparison does not run external framework engines" in text
