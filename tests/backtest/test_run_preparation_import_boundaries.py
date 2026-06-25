from __future__ import annotations

from pathlib import Path


def test_runner_delegates_run_preparation() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    preparation_text = Path("src/sis/backtest/engine/run_preparation.py").read_text(
        encoding="utf-8"
    )

    assert "prepare_backtest_inputs" in runner_text
    assert "normalize_trade_xyz_market_data" not in runner_text
    assert "evaluate_data_quality" not in runner_text
    assert "build_data_manifest" not in runner_text
    assert "apply_period_filter" not in runner_text
    assert "_first_string" not in runner_text
    assert "normalize_trade_xyz_market_data" in preparation_text
    assert "evaluate_data_quality" in preparation_text
    assert "build_data_manifest" in preparation_text
    assert "apply_period_filter" in preparation_text
