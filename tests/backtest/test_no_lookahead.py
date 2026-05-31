from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.fill import next_fill_row_index
from sis.backtest.engine.runner import BreakoutParameters, run_backtest


def test_next_fill_row_index_uses_row_after_signal() -> None:
    assert next_fill_row_index(signal_row_index=0, row_count=3) == 1
    assert next_fill_row_index(signal_row_index=1, row_count=3) == 2


def test_next_fill_row_index_returns_none_when_no_future_row_exists() -> None:
    assert next_fill_row_index(signal_row_index=2, row_count=3) is None


def test_runner_never_uses_signal_row_close_as_fill_price(tmp_path) -> None:
    frame = pl.DataFrame(
        {
            "event_ts": [datetime(2026, 1, 1, hour, tzinfo=timezone.utc) for hour in range(4)],
            "symbol": ["SP500"] * 4,
            "close": [100.0, 101.0, 10_000.0, 90.0],
            "best_bid": [99.9, 100.9, 102.9, 89.9],
            "best_ask": [100.1, 101.1, 103.1, 90.1],
            "taker_fee_bps": [9.0] * 4,
            "maker_fee_bps": [3.0] * 4,
            "market_status": ["open"] * 4,
            "is_tradable": [True] * 4,
            "block_reasons": [[] for _ in range(4)],
        }
    )
    config = BacktestConfig(
        run_id="no-lookahead-fill",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 4, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )

    result = run_backtest(
        config=config,
        market_data=frame,
        out_dir=tmp_path,
        input_data_ref="fixture://no-lookahead",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    fills = pl.read_parquet(result.run_dir / "fills.parquet")
    assert fills.get_column("event_ts").to_list() == [datetime(2026, 1, 1, 3, tzinfo=timezone.utc)]
    assert fills.select("fill_price").item() == 90.1
    assert fills.select("fill_price_source").item() == "best_ask"
