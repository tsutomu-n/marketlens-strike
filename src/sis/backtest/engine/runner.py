from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.end_position_policy import (
    BacktestError as _BacktestError,
)
from sis.backtest.engine.funding_events import build_funding_event_rows
from sis.backtest.engine.run_completion import complete_backtest_run
from sis.backtest.engine.run_execution import execute_backtest_rows
from sis.backtest.engine.run_preparation import prepare_backtest_inputs
from sis.backtest.engine.run_result import BacktestRunResult
from sis.backtest.engine.run_state import initialize_backtest_run_state
from sis.backtest.engine.run_loop import (
    BreakoutParameters,
)

BacktestError = _BacktestError


def run_backtest(
    *,
    config: BacktestConfig,
    market_data: pl.DataFrame,
    out_dir: Path,
    input_data_ref: str,
    funding_events: pl.DataFrame | None = None,
    funding_events_ref: str | None = None,
    breakout: BreakoutParameters | None = None,
) -> BacktestRunResult:
    breakout = breakout or BreakoutParameters()
    prepared = prepare_backtest_inputs(
        config=config,
        market_data=market_data,
        input_data_ref=input_data_ref,
        breakout=breakout,
    )
    rows = prepared.rows
    funding_event_rows = build_funding_event_rows(funding_events, config=config)
    state = initialize_backtest_run_state(initial_cash_usd=config.initial_cash_usd)

    state = execute_backtest_rows(
        rows=rows,
        funding_event_rows=funding_event_rows,
        state=state,
        config=config,
        breakout=breakout,
    )

    return complete_backtest_run(
        config=config,
        prepared=prepared,
        state=state,
        out_dir=out_dir,
        input_data_ref=input_data_ref,
        funding_events_ref=funding_events_ref,
        funding_event_count=len(funding_event_rows),
        breakout=breakout,
    )
