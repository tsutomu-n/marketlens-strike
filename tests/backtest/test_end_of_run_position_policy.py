from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.engine.config import (
    BacktestConfig,
    ExecutionConfig,
    PeriodConfig,
    PositionSizingConfig,
)
from sis.backtest.engine.runner import BacktestError, BreakoutParameters, run_backtest


def _config(policy: str, run_id: str = "end-policy") -> BacktestConfig:
    return BacktestConfig(
        run_id=run_id,
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            warmup_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_start_ts=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 4, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
        execution=ExecutionConfig(end_position_policy=policy),
    )


def _frame(last_price: float | None = 104.0) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "event_ts": [datetime(2026, 1, 1, hour, tzinfo=timezone.utc) for hour in range(4)],
            "symbol": ["SP500"] * 4,
            "close": [100.0, 101.0, 103.0, 104.0],
            "best_bid": [99.9, 100.9, 102.9, last_price],
            "best_ask": [100.1, 101.1, 103.1, None if last_price is None else last_price + 0.2],
            "taker_fee_bps": [9.0] * 4,
            "maker_fee_bps": [3.0] * 4,
            "market_status": ["open"] * 4,
            "is_tradable": [True] * 4,
            "block_reasons": [[] for _ in range(4)],
        }
    )


def test_force_close_if_executable_closes_only_with_executable_last_row(tmp_path) -> None:
    result = run_backtest(
        config=_config("force_close_if_executable"),
        market_data=_frame(),
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=1, exit_lookback=10),
    )

    assert result.metrics["open_position_at_end"] is False


def test_mark_to_market_only_leaves_open_position_without_fill(tmp_path) -> None:
    result = run_backtest(
        config=_config("mark_to_market_only", run_id="mtm"),
        market_data=_frame(),
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=1, exit_lookback=10),
    )

    assert result.metrics["open_position_at_end"] is True


def test_error_if_open_raises(tmp_path) -> None:
    with pytest.raises(BacktestError):
        run_backtest(
            config=_config("error_if_open", run_id="error"),
            market_data=_frame(),
            out_dir=tmp_path,
            input_data_ref="fixture://sp500",
            breakout=BreakoutParameters(entry_lookback=1, exit_lookback=10),
        )
