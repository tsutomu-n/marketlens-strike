from __future__ import annotations

from pathlib import Path


def test_runner_imports_run_result_contract_without_defining_it() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    result_text = Path("src/sis/backtest/engine/run_result.py").read_text(encoding="utf-8")

    assert "from sis.backtest.engine.run_result import BacktestRunResult" in runner_text
    assert "class BacktestRunResult" not in runner_text
    assert "@dataclass(frozen=True)" not in runner_text
    assert "class BacktestRunResult" in result_text
    assert "@dataclass(frozen=True)" in result_text
