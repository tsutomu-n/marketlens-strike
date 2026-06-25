from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.result_assembly import (
    build_parameter_rows,
    build_scenario_rows,
    build_split_summary,
)
from sis.backtest.engine.run_loop import BreakoutParameters


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="result-assembly",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )


def test_build_scenario_rows_preserves_cost_delta_formula() -> None:
    rows = build_scenario_rows(
        config=_config(),
        metrics={
            "net_return_after_cost": 0.1,
            "fee_impact": 100.0,
            "turnover": 1_000.0,
        },
    )

    assert [row["scenario"] for row in rows] == [
        "base",
        "fee_2x",
        "slippage_5bps",
        "conservative",
    ]
    assert rows[0] == {
        "scenario": "base",
        "scenario_method": "cost_derived_v0",
        "fee_multiplier": 1.0,
        "extra_slippage_bps": 0.0,
        "net_return_after_cost": pytest.approx(0.1),
    }
    assert rows[-1]["net_return_after_cost"] == pytest.approx(0.0899)


def test_build_split_summary_uses_exit_timestamps_for_trade_counts() -> None:
    times = [datetime(2026, 1, 1, hour, tzinfo=timezone.utc) for hour in range(4)]
    market_frame = pl.DataFrame({"event_ts": times, "close": [100.0, 110.0, 105.0, 120.0]})
    equity_frame = pl.DataFrame({"event_ts": times, "equity": [100.0, 110.0, 105.0, 120.0]})
    trades_frame = pl.DataFrame({"exit_ts": [times[1], times[3]]})

    summary = build_split_summary(
        market_frame=market_frame,
        equity_frame=equity_frame,
        trades_frame=trades_frame,
    )

    assert summary["oos_validation_done"] is True
    assert summary["train_return"] == pytest.approx(0.1)
    assert summary["test_return"] == pytest.approx(120.0 / 105.0 - 1.0)
    assert summary["train_max_drawdown"] == pytest.approx(0.0)
    assert summary["test_max_drawdown"] == pytest.approx(0.0)
    assert summary["train_trade_count"] == 1
    assert summary["test_trade_count"] == 1


def test_build_parameter_rows_preserves_grid_and_penalty_formula() -> None:
    rows = build_parameter_rows(
        metrics={"net_return_after_cost": 0.2},
        breakout=BreakoutParameters(entry_lookback=20, exit_lookback=10),
    )

    assert len(rows) == 9
    current = next(
        row for row in rows if row["entry_lookback"] == 20 and row["exit_lookback"] == 10
    )
    penalized = next(
        row for row in rows if row["entry_lookback"] == 10 and row["exit_lookback"] == 5
    )
    assert current["net_return_after_cost"] == pytest.approx(0.2)
    assert penalized["net_return_after_cost"] == pytest.approx(0.1985)
    assert all(row["best_parameter_is_in_sample_only"] is True for row in rows)
