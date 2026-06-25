from __future__ import annotations

from pathlib import Path

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.end_position_policy import apply_end_position_policy
from sis.backtest.engine.run_finalization import finalize_backtest_run
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.run_outputs import build_run_outputs
from sis.backtest.engine.run_preparation import PreparedBacktestInputs
from sis.backtest.engine.run_result import BacktestRunResult
from sis.backtest.engine.run_state import BacktestRunState


def complete_backtest_run(
    *,
    config: BacktestConfig,
    prepared: PreparedBacktestInputs,
    state: BacktestRunState,
    out_dir: Path,
    input_data_ref: str,
    funding_events_ref: str | None,
    funding_event_count: int,
    breakout: BreakoutParameters,
) -> BacktestRunResult:
    state.portfolio, state.open_trade = apply_end_position_policy(
        config=config,
        rows=prepared.rows,
        portfolio=state.portfolio,
        open_trade=state.open_trade,
        orders=state.orders,
        fills=state.fills,
        blocked=state.blocked,
        trades=state.trades,
        equity_rows=state.equity_rows,
    )
    outputs = build_run_outputs(
        initial_cash_usd=config.initial_cash_usd,
        orders=state.orders,
        fills=state.fills,
        trades=state.trades,
        blocked=state.blocked,
        equity_rows=state.equity_rows,
        portfolio=state.portfolio,
        end_position_policy=config.execution.end_position_policy,
        funding_events_ref=funding_events_ref,
        funding_event_count=funding_event_count,
    )
    run_dir = finalize_backtest_run(
        config=config,
        normalized=prepared.normalized,
        filtered=prepared.filtered,
        out_dir=out_dir,
        input_data_ref=input_data_ref,
        data_quality=prepared.quality,
        data_manifest=prepared.manifest,
        event_time_source=prepared.event_time_source,
        close_source=prepared.close_source,
        outputs=outputs,
        breakout=breakout,
    )
    return BacktestRunResult(run_dir=run_dir, metrics=outputs.metrics)
