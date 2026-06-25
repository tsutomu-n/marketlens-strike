from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sis.backtest.engine.run_result import BacktestRunResult


def test_backtest_run_result_exposes_run_dir_and_metrics() -> None:
    result = BacktestRunResult(run_dir=Path("data/backtest/run"), metrics={"trades": 1})

    assert result.run_dir == Path("data/backtest/run")
    assert result.metrics == {"trades": 1}


def test_backtest_run_result_is_frozen() -> None:
    result = BacktestRunResult(run_dir=Path("data/backtest/run"), metrics={})

    with pytest.raises(FrozenInstanceError):
        result.run_dir = Path("other")  # type: ignore[misc]
