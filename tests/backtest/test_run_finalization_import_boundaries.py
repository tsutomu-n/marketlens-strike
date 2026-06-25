from __future__ import annotations

from pathlib import Path


def test_runner_delegates_run_finalization() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    completion_text = Path("src/sis/backtest/engine/run_completion.py").read_text(encoding="utf-8")
    finalization_text = Path("src/sis/backtest/engine/run_finalization.py").read_text(
        encoding="utf-8"
    )

    assert "complete_backtest_run" in runner_text
    assert "finalize_backtest_run" not in runner_text
    assert "finalize_backtest_run" in completion_text
    assert "run_benchmarks" not in runner_text
    assert "write_backtest_artifacts" not in runner_text
    assert "build_scenario_rows" not in runner_text
    assert "build_split_summary" not in runner_text
    assert "build_parameter_rows" not in runner_text
    assert "run_benchmarks" in finalization_text
    assert "write_backtest_artifacts" in finalization_text
    assert "build_scenario_rows" in finalization_text
    assert "build_split_summary" in finalization_text
    assert "build_parameter_rows" in finalization_text
