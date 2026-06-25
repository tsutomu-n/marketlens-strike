from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast

from sis.backtest.metrics import BacktestMetrics
from sis.research.strategy_lab.authoring.backtest import (
    write_authoring_backtest_outputs as backtest_write_authoring_backtest_outputs,
)
from sis.research.strategy_lab.authoring.backtest_outputs import (
    write_authoring_backtest_outputs,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _spec() -> StrategyAuthoringSpec:
    return cast(
        StrategyAuthoringSpec,
        SimpleNamespace(experiment=SimpleNamespace(strategy_id="output_writer_test")),
    )


def _metrics() -> list[BacktestMetrics]:
    return [
        BacktestMetrics(
            venue="sim",
            canonical_symbol="NDX",
            total_return=0.125,
            annual_return=None,
            max_drawdown=-0.034,
            sharpe=None,
            win_rate=0.6,
            profit_factor=None,
            trade_count=7,
            avg_trade_return=None,
            worst_trade=None,
            exposure_ratio=1.0,
            cost_drag_bps=2.5,
            cost_source="fixture",
            stale_rejected_count=1,
            halt_rejected_count=0,
        )
    ]


def _summary() -> dict[str, object]:
    return {
        "source_signal_count": 10,
        "evaluation_signal_count": 8,
        "evaluation_window": {
            "evaluation_start_at": "2026-01-01T00:00:00",
            "evaluation_end_at": "2026-01-31T00:00:00",
        },
        "signals_considered": 8,
        "executed_count": 7,
        "pass_min_trade_count": True,
        "pass_all_thresholds": True,
        "backtest_passed": True,
        "capital": {
            "initial_capital_usd": 10000.0,
            "net_pnl_usd": 1250.0,
            "ending_equity_usd": 11250.0,
            "max_drawdown_loss_usd": 340.0,
        },
        "strategy_scorecard": {
            "derived_feature_count": 2,
            "failed_thresholds": [],
            "derived_feature_ops": {"rolling_mean": 1, "zscore": 1},
            "block_reason_counts": {"risk_throttle": 2},
        },
    }


def test_backtest_outputs_module_writes_metrics_json_and_report(tmp_path) -> None:
    artifacts = write_authoring_backtest_outputs(_spec(), _metrics(), _summary(), data_dir=tmp_path)

    assert artifacts == {
        "metrics": tmp_path / "research/strategy_backtest_metrics.json",
        "report": tmp_path / "reports/strategy_backtest_report.md",
    }
    payload = json.loads(artifacts["metrics"].read_text(encoding="utf-8"))
    assert payload["schema_version"] == "strategy_authoring_backtest_result.v1"
    assert payload["strategy_id"] == "output_writer_test"
    assert payload["paper_only"] is True
    assert payload["live_order_submitted"] is False
    assert payload["summary"]["backtest_passed"] is True
    assert payload["metrics"][0]["canonical_symbol"] == "NDX"
    assert payload["metrics"][0]["trade_count"] == 7

    report = artifacts["report"].read_text(encoding="utf-8")
    assert "# Strategy Authoring Backtest Report" in report
    assert "paper_only: true" in report
    assert "- strategy_id: output_writer_test" in report
    assert "- initial_capital_usd: 10000.0" in report
    assert "- rolling_mean: 1" in report
    assert "- risk_throttle: 2" in report
    assert "| sim | NDX | 7 | 0.125000 | -0.034000 | 2.50 |" in report


def test_backtest_module_keeps_output_writer_compatibility_import() -> None:
    assert backtest_write_authoring_backtest_outputs is write_authoring_backtest_outputs
