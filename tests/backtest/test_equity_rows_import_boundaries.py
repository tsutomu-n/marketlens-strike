from __future__ import annotations

from pathlib import Path


def test_runner_delegates_equity_row_construction() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    execution_text = Path("src/sis/backtest/engine/run_execution.py").read_text(encoding="utf-8")
    equity_text = Path("src/sis/backtest/engine/equity_rows.py").read_text(encoding="utf-8")

    assert "execute_backtest_rows" in runner_text
    assert "_equity_row" not in runner_text
    assert "_equity_row" in execution_text
    assert "mark_price =" not in runner_text
    assert "mark_price =" in equity_text
    assert '"unrealized_pnl": unrealized' not in runner_text
    assert '"unrealized_pnl": unrealized' in equity_text
    assert '"session_type": str(row.get("session_type") or "unknown")' not in runner_text
    assert 'equity_rows[-1]["cash_usd"]' not in runner_text
