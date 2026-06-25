from __future__ import annotations

from pathlib import Path


def test_runner_delegates_funding_application_details() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    execution_text = Path("src/sis/backtest/engine/run_execution.py").read_text(encoding="utf-8")

    assert "execute_backtest_rows" in runner_text
    assert "apply_external_funding_before_signal" not in runner_text
    assert "apply_quote_row_funding_after_signal" not in runner_text
    assert "apply_external_funding_after_loop" not in runner_text
    assert "apply_external_funding_before_signal" in execution_text
    assert "apply_quote_row_funding_after_signal" in execution_text
    assert "apply_external_funding_after_loop" in execution_text
    assert "_apply_due_funding_events" not in runner_text
    assert "_apply_quote_row_funding" not in runner_text
    assert "if use_external_funding_events" not in runner_text
    assert "if not use_external_funding_events" not in runner_text
    assert "calculate_v0_funding_amount" not in runner_text
    assert "funding_warning" not in runner_text
    assert "portfolio.apply_funding" not in runner_text
