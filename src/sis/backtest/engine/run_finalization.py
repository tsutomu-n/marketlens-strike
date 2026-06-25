from __future__ import annotations

from pathlib import Path

import polars as pl
from pydantic import BaseModel

from sis.backtest.engine.artifacts import write_backtest_artifacts
from sis.backtest.engine.benchmark import run_benchmarks
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.result_assembly import (
    build_parameter_rows,
    build_scenario_rows,
    build_split_summary,
)
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.run_outputs import BacktestRunOutputs


def finalize_backtest_run(
    *,
    config: BacktestConfig,
    normalized: pl.DataFrame,
    filtered: pl.DataFrame,
    out_dir: Path,
    input_data_ref: str,
    data_quality: BaseModel,
    data_manifest: BaseModel,
    event_time_source: str,
    close_source: str,
    outputs: BacktestRunOutputs,
    breakout: BreakoutParameters,
) -> Path:
    benchmark_results, benchmark_equity = run_benchmarks(config=config, frame=normalized)
    scenario_rows = build_scenario_rows(config=config, metrics=outputs.metrics)
    split_summary = build_split_summary(
        market_frame=filtered,
        equity_frame=outputs.equity_frame,
        trades_frame=outputs.trades_frame,
    )
    parameter_rows = build_parameter_rows(metrics=outputs.metrics, breakout=breakout)

    run_dir = out_dir / config.run_id
    write_backtest_artifacts(
        run_dir=run_dir,
        config=config,
        normalized=normalized,
        input_data_ref=input_data_ref,
        data_quality=data_quality,
        data_manifest=data_manifest,
        event_time_source=event_time_source,
        close_source=close_source,
        metrics=outputs.metrics,
        benchmark_results=benchmark_results,
        scenario_rows=scenario_rows,
        split_summary=split_summary,
        parameter_rows=parameter_rows,
        orders_frame=outputs.orders_frame,
        fills_frame=outputs.fills_frame,
        trades_frame=outputs.trades_frame,
        blocked_frame=outputs.blocked_frame,
        equity_frame=outputs.equity_frame,
        benchmark_equity=benchmark_equity,
    )
    return run_dir
