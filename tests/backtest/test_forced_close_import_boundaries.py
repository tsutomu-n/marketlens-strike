from __future__ import annotations

from pathlib import Path


def test_runner_delegates_forced_close_details() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    completion_text = Path("src/sis/backtest/engine/run_completion.py").read_text(encoding="utf-8")
    policy_text = Path("src/sis/backtest/engine/end_position_policy.py").read_text(encoding="utf-8")

    assert "complete_backtest_run" in runner_text
    assert "apply_end_position_policy" not in runner_text
    assert "apply_end_position_policy" in completion_text
    assert "_apply_forced_end_close" not in runner_text
    assert "_apply_forced_end_close" in policy_text
    assert 'signal_id="forced_end_close"' not in runner_text
    assert "force_order" not in runner_text
    assert "requested_qty=portfolio.position_qty" not in runner_text
