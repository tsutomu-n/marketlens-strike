from __future__ import annotations

from pathlib import Path


def test_runner_delegates_signal_order_scheduling_details() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    execution_text = Path("src/sis/backtest/engine/run_execution.py").read_text(encoding="utf-8")
    scheduling_text = Path("src/sis/backtest/engine/order_scheduling.py").read_text(
        encoding="utf-8"
    )

    assert "execute_backtest_rows" in runner_text
    assert "_schedule_signal_order" not in runner_text
    assert "_schedule_signal_order" in execution_text
    assert "next_fill_row_index" not in runner_text
    assert "next_fill_row_index" in scheduling_text
    assert "signal_kind" not in runner_text
    assert "signal_kind" in scheduling_text
    assert "evaluate_entry_gate" not in runner_text
    assert "evaluate_exit_gate" not in runner_text
    assert "no_future_fill_row" not in runner_text
    assert "pending_orders[fill_index]" not in runner_text
