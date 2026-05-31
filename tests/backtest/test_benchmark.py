from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.benchmark import run_benchmarks
from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.trade_xyz.schema import normalize_trade_xyz_market_data


def test_run_benchmarks_outputs_cash_and_buy_hold_like() -> None:
    config = BacktestConfig(
        run_id="run-001",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )
    frame = normalize_trade_xyz_market_data(
        pl.DataFrame(
            {
                "event_ts": [
                    datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
                ],
                "symbol": ["SP500", "SP500", "SP500"],
                "best_ask": [100.0, 101.0, 102.0],
                "best_bid": [99.0, 100.0, 101.0],
                "mid_price": [99.5, 100.5, 101.5],
                "taker_fee_bps": [9.0, 9.0, 9.0],
                "maker_fee_bps": [3.0, 3.0, 3.0],
                "is_tradable": [True, True, True],
                "block_reasons": [[], [], []],
            }
        ),
        symbol="SP500",
    )

    results, equity = run_benchmarks(config=config, frame=frame)

    assert results["cash_only"]["status"] == "ok"
    assert results["buy_and_hold_like"]["status"] == "ok"
    assert equity.height == 6
    assert equity.get_column("benchmark").unique().sort().to_list() == [
        "buy_and_hold_like",
        "cash_only",
    ]
