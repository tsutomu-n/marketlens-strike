from __future__ import annotations

from pathlib import Path


def test_runner_delegates_pending_fill_execution() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    execution_text = Path("src/sis/backtest/engine/run_execution.py").read_text(encoding="utf-8")
    pending_fill_text = Path("src/sis/backtest/engine/pending_fill_execution.py").read_text(
        encoding="utf-8"
    )

    assert "execute_backtest_rows" in runner_text
    assert "_apply_pending_order_fill" not in runner_text
    assert "_apply_pending_order_fill" in execution_text
    assert "_fill_order" not in runner_text
    assert "_apply_trade_lifecycle_fill" not in runner_text
    assert "_fill_order" in pending_fill_text
    assert "_apply_trade_lifecycle_fill" in pending_fill_text
