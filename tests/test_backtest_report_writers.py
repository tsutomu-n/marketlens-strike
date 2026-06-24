from __future__ import annotations

import json

from sis.backtest import report_writers
from sis.backtest.bridge import (
    write_backtest_metrics_json as bridge_write_backtest_metrics_json,
    write_backtest_metrics_summary_json as bridge_write_backtest_metrics_summary_json,
    write_backtest_report as bridge_write_backtest_report,
)
from sis.backtest.metrics import BacktestMetrics


def _metrics() -> list[BacktestMetrics]:
    return [
        BacktestMetrics(
            venue="gtrade",
            canonical_symbol="QQQ",
            trade_count=2,
            avg_trade_return=0.03,
            total_return=0.06,
            annual_return=0.12,
            sharpe=1.1,
            max_drawdown=-0.01,
            win_rate=0.5,
            profit_factor=1.5,
            worst_trade=-0.02,
            cost_drag_bps=7.0,
            cost_source="matrix",
            stale_rejected_count=1,
            halt_rejected_count=0,
            exposure_ratio=1.0,
        )
    ]


def test_bridge_reexports_report_writers_for_compatibility() -> None:
    assert bridge_write_backtest_report is report_writers.write_backtest_report
    assert bridge_write_backtest_metrics_json is report_writers.write_backtest_metrics_json
    assert (
        bridge_write_backtest_metrics_summary_json
        is report_writers.write_backtest_metrics_summary_json
    )


def test_report_writer_module_writes_metrics_json(tmp_path) -> None:
    out = tmp_path / "metrics.json"

    report_writers.write_backtest_metrics_json(_metrics(), out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload == [
        {
            "venue": "gtrade",
            "canonical_symbol": "QQQ",
            "trade_count": 2,
            "avg_trade_return": 0.03,
            "total_return": 0.06,
            "annual_return": 0.12,
            "sharpe": 1.1,
            "max_drawdown": -0.01,
            "win_rate": 0.5,
            "profit_factor": 1.5,
            "worst_trade": -0.02,
            "cost_drag_bps": 7.0,
            "cost_source": "matrix",
            "stale_rejected_count": 1,
            "halt_rejected_count": 0,
            "exposure_ratio": 1.0,
        }
    ]
