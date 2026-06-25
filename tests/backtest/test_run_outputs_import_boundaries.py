from __future__ import annotations

from pathlib import Path


def test_runner_delegates_run_output_frame_and_metric_assembly() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    completion_text = Path("src/sis/backtest/engine/run_completion.py").read_text(encoding="utf-8")

    assert "complete_backtest_run" in runner_text
    assert "build_run_outputs" not in runner_text
    assert "build_run_outputs" in completion_text
    assert "orders_to_frame" not in runner_text
    assert "fills_to_frame" not in runner_text
    assert "trades_to_frame" not in runner_text
    assert "blocked_events_to_frame" not in runner_text
    assert "equity_to_frame" not in runner_text
    assert "calculate_metrics" not in runner_text
    assert "enrich_run_metrics" not in runner_text
