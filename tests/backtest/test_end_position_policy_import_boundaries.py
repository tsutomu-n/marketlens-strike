from __future__ import annotations

from pathlib import Path


def test_runner_delegates_end_position_policy() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    completion_text = Path("src/sis/backtest/engine/run_completion.py").read_text(encoding="utf-8")
    policy_text = Path("src/sis/backtest/engine/end_position_policy.py").read_text(encoding="utf-8")

    assert "complete_backtest_run" in runner_text
    assert "apply_end_position_policy" not in runner_text
    assert "apply_end_position_policy" in completion_text
    assert "_apply_forced_end_close" not in runner_text
    assert '"error_if_open"' not in runner_text
    assert '"force_close_if_executable"' not in runner_text
    assert "open position at end of run" not in runner_text
    assert "_apply_forced_end_close" in policy_text
    assert '"error_if_open"' in policy_text
    assert '"force_close_if_executable"' in policy_text
    assert "open position at end of run" in policy_text
