from __future__ import annotations

from datetime import datetime, timezone
import json

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.funding_events import build_funding_event_rows
from sis.backtest.engine.run_completion import complete_backtest_run
from sis.backtest.engine.run_execution import execute_backtest_rows
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.run_preparation import prepare_backtest_inputs
from sis.backtest.engine.run_result import BacktestRunResult
from sis.backtest.engine.run_state import initialize_backtest_run_state


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="run-completion",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            warmup_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_start_ts=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 6, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "event_ts": [
                datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 4, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 5, tzinfo=timezone.utc),
            ],
            "symbol": ["SP500"] * 6,
            "close": [100.0, 101.0, 103.0, 102.0, 99.0, 98.0],
            "best_bid": [99.9, 100.9, 102.9, 101.9, 98.9, 97.9],
            "best_ask": [100.1, 101.1, 103.1, 102.1, 99.1, 98.1],
            "taker_fee_bps": [9.0] * 6,
            "maker_fee_bps": [3.0] * 6,
            "market_status": ["open"] * 6,
            "is_tradable": [True] * 6,
            "block_reasons": [[] for _ in range(6)],
        }
    )


def test_complete_backtest_run_applies_policy_writes_artifacts_and_returns_result(
    tmp_path,
) -> None:
    config = _config()
    breakout = BreakoutParameters(entry_lookback=2, exit_lookback=2)
    prepared = prepare_backtest_inputs(
        config=config,
        market_data=_frame(),
        input_data_ref="fixture://sp500",
        breakout=breakout,
    )
    funding_event_rows = build_funding_event_rows(None, config=config)
    state = execute_backtest_rows(
        rows=prepared.rows,
        funding_event_rows=funding_event_rows,
        state=initialize_backtest_run_state(initial_cash_usd=config.initial_cash_usd),
        config=config,
        breakout=breakout,
    )

    result = complete_backtest_run(
        config=config,
        prepared=prepared,
        state=state,
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        funding_events_ref=None,
        funding_event_count=len(funding_event_rows),
        breakout=breakout,
    )

    assert isinstance(result, BacktestRunResult)
    assert result.run_dir == tmp_path / "run-completion"
    assert (result.run_dir / "backtest_run.json").exists()
    assert (result.run_dir / "metrics.json").exists()
    assert result.metrics == json.loads(
        (result.run_dir / "metrics.json").read_text(encoding="utf-8")
    )
