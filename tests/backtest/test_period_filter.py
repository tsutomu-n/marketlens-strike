from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.data_quality import apply_period_filter


def test_period_filter_keeps_warmup_rows_but_marks_evaluation_window() -> None:
    config = BacktestConfig(
        run_id="run-001",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            warmup_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_start_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )
    frame = pl.DataFrame(
        {
            "event_ts": [
                datetime(2025, 12, 31, 23, tzinfo=timezone.utc),
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 2, tzinfo=timezone.utc),
                datetime(2026, 1, 3, tzinfo=timezone.utc),
            ],
            "symbol": ["SP500", "SP500", "SP500", "SP500"],
        }
    )

    filtered = apply_period_filter(frame, config=config)

    assert filtered.select("event_ts").to_series().to_list() == [
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 2, tzinfo=timezone.utc),
    ]
    assert filtered.select("is_evaluation").to_series().to_list() == [False, True]
