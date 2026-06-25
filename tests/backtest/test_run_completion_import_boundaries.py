from __future__ import annotations

from pathlib import Path


def test_runner_delegates_run_completion() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    completion_text = Path("src/sis/backtest/engine/run_completion.py").read_text(encoding="utf-8")

    assert "complete_backtest_run" in runner_text
    assert "apply_end_position_policy" not in runner_text
    assert "build_run_outputs" not in runner_text
    assert "finalize_backtest_run" not in runner_text
    assert "BacktestRunResult(run_dir=run_dir" not in runner_text

    assert "apply_end_position_policy" in completion_text
    assert "build_run_outputs" in completion_text
    assert "finalize_backtest_run" in completion_text
    assert "BacktestRunResult(run_dir=run_dir" in completion_text
