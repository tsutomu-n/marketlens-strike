from __future__ import annotations

from pathlib import Path


def test_runner_delegates_run_state_initialization() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    state_text = Path("src/sis/backtest/engine/run_state.py").read_text(encoding="utf-8")

    assert "initialize_backtest_run_state" in runner_text
    assert "Portfolio.flat" not in runner_text
    assert "orders: list" not in runner_text
    assert "fills: list" not in runner_text
    assert "blocked: list" not in runner_text
    assert "pending_orders: dict" not in runner_text
    assert "recorded_warnings: set" not in runner_text
    assert "next_funding_event_index = 0" not in runner_text
    assert "Portfolio.flat" in state_text
    assert "class BacktestRunState" in state_text
