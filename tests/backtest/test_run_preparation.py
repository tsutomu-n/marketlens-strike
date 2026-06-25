from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.run_preparation import prepare_backtest_inputs


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="preparation-run",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            warmup_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_start_ts=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )


def _market_data() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "event_ts": [
                datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
            ],
            "symbol": ["SP500", "SP500", "SP500"],
            "close": [100.0, 101.0, 102.0],
            "best_bid": [99.0, 100.0, 101.0],
            "best_ask": [100.0, 101.0, 102.0],
            "taker_fee_bps": [9.0, 9.0, 9.0],
            "maker_fee_bps": [3.0, 3.0, 3.0],
            "market_status": ["open", "open", "open"],
            "is_tradable": [True, True, True],
            "block_reasons": [[], [], []],
            "event_time_source": ["ts_client", "ts_client", "ts_client"],
            "close_source": ["mid_price", "mid_price", "mid_price"],
            "bar_builder": ["quote_bar_v1", "quote_bar_v1", "quote_bar_v1"],
        }
    )


def test_prepare_backtest_inputs_builds_manifest_and_filtered_rows() -> None:
    prepared = prepare_backtest_inputs(
        config=_config(),
        market_data=_market_data(),
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=1, exit_lookback=1),
    )

    assert prepared.quality.status == "warn"
    assert prepared.event_time_source == "ts_client"
    assert prepared.close_source == "mid_price"
    assert prepared.bar_builder == "quote_bar_v1"
    assert prepared.manifest.event_time_source == "ts_client"
    assert prepared.manifest.close_source == "mid_price"
    assert prepared.manifest.bar_builder == "quote_bar_v1"
    assert prepared.filtered.get_column("_row_index").to_list() == [0, 1, 2]
    assert [row["_row_index"] for row in prepared.rows] == [0, 1, 2]
    assert prepared.rows[0]["is_evaluation"] is False
    assert prepared.rows[1]["is_evaluation"] is True


def test_prepare_backtest_inputs_raises_existing_normalization_failure_message() -> None:
    market_data = _market_data().drop("is_tradable")

    with pytest.raises(ValueError, match="missing required columns: is_tradable"):
        prepare_backtest_inputs(
            config=_config(),
            market_data=market_data,
            input_data_ref="fixture://sp500",
            breakout=BreakoutParameters(entry_lookback=1, exit_lookback=1),
        )
