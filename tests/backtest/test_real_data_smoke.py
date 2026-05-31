from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from sis.backtest.engine.config import (
    BacktestConfig,
    ExecutionConfig,
    PeriodConfig,
    PositionSizingConfig,
)
from sis.backtest.engine.runner import BreakoutParameters, run_backtest
from sis.backtest.trade_xyz.schema import normalize_trade_xyz_market_data


def test_real_normalized_quotes_sp500_smoke_when_available(tmp_path) -> None:
    path = Path("data/normalized/quotes.parquet")
    if not path.exists():
        pytest.skip("data/normalized/quotes.parquet is not available")

    raw = pl.read_parquet(path).filter(pl.col("canonical_symbol") == "SP500")
    if raw.is_empty():
        pytest.skip("SP500 rows are not available in normalized quotes")

    normalized = normalize_trade_xyz_market_data(raw, symbol="SP500")
    config = BacktestConfig(
        run_id="real-sp500-smoke",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="raw_quote",
        period=PeriodConfig(
            evaluation_start_ts=normalized.get_column("event_ts").min(),
            evaluation_end_ts=normalized.get_column("event_ts").max(),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
        execution=ExecutionConfig(force_close_on_end=True),
    )

    result = run_backtest(
        config=config,
        market_data=raw,
        out_dir=tmp_path,
        input_data_ref=f"{path}#SP500",
        breakout=BreakoutParameters(entry_lookback=3, exit_lookback=2),
    )

    data_quality = result.run_dir / "data_quality.json"
    assert data_quality.exists()
    assert '"status": "fail"' not in data_quality.read_text(encoding="utf-8")
    assert (result.run_dir / "backtest_run.json").exists()
    assert (result.run_dir / "metrics.json").exists()
