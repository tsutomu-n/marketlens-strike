from __future__ import annotations

from pathlib import Path


def test_runner_delegates_row_loop_execution() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    execution_text = Path("src/sis/backtest/engine/run_execution.py").read_text(encoding="utf-8")

    assert "execute_backtest_rows" in runner_text
    assert "for index, row in enumerate(rows):" not in runner_text
    assert "_apply_pending_order_fill" not in runner_text
    assert "_schedule_signal_order" not in runner_text
    assert "apply_external_funding_before_signal" not in runner_text
    assert "apply_quote_row_funding_after_signal" not in runner_text
    assert "apply_external_funding_after_loop" not in runner_text
    assert "_equity_row" not in runner_text

    assert "for index, row in enumerate(rows):" in execution_text
    assert "_apply_pending_order_fill" in execution_text
    assert "_schedule_signal_order" in execution_text
    assert "apply_external_funding_before_signal" in execution_text
    assert "apply_quote_row_funding_after_signal" in execution_text
    assert "apply_external_funding_after_loop" in execution_text
    assert "_equity_row" in execution_text
