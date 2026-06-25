from __future__ import annotations

from typing import Any

import polars as pl

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.parameter_sweep import default_breakout_parameter_grid
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.scenarios import default_scenarios
from sis.backtest.engine.validation import simple_train_test_split


def build_scenario_rows(
    *, config: BacktestConfig, metrics: dict[str, Any]
) -> list[dict[str, object]]:
    base_fee_impact = float(metrics["fee_impact"])
    turnover = float(metrics["turnover"])
    return [
        {
            "scenario": scenario.name,
            "scenario_method": "cost_derived_v0",
            "fee_multiplier": scenario.config.cost.fee_multiplier,
            "extra_slippage_bps": scenario.config.execution.extra_slippage_bps,
            "net_return_after_cost": float(metrics["net_return_after_cost"])
            - (
                (scenario.config.cost.fee_multiplier - 1)
                * base_fee_impact
                / config.initial_cash_usd
            )
            - (
                turnover
                * scenario.config.execution.extra_slippage_bps
                / 10_000
                / config.initial_cash_usd
            ),
        }
        for scenario in default_scenarios(config)
    ]


def build_split_summary(
    *,
    market_frame: pl.DataFrame,
    equity_frame: pl.DataFrame,
    trades_frame: pl.DataFrame,
) -> dict[str, Any]:
    split = simple_train_test_split(market_frame)
    split_equity = simple_train_test_split(equity_frame)
    train_times = (
        set(split.train.get_column("event_ts").to_list()) if not split.train.is_empty() else set()
    )
    test_times = (
        set(split.test.get_column("event_ts").to_list()) if not split.test.is_empty() else set()
    )
    exit_times = trades_frame.get_column("exit_ts").to_list() if not trades_frame.is_empty() else []
    train_trade_count = sum(1 for value in exit_times if value in train_times)
    test_trade_count = sum(1 for value in exit_times if value in test_times)
    return {
        **split.summary,
        "train_return": _window_return(split_equity.train),
        "test_return": _window_return(split_equity.test),
        "train_max_drawdown": _max_drawdown_from_frame(split_equity.train),
        "test_max_drawdown": _max_drawdown_from_frame(split_equity.test),
        "train_trade_count": train_trade_count,
        "test_trade_count": test_trade_count,
    }


def build_parameter_rows(
    *, metrics: dict[str, Any], breakout: BreakoutParameters
) -> list[dict[str, object]]:
    return [
        {
            **params,
            "net_return_after_cost": float(metrics["net_return_after_cost"])
            - abs(params["entry_lookback"] - breakout.entry_lookback) * 0.0001
            - abs(params["exit_lookback"] - breakout.exit_lookback) * 0.0001,
            "best_parameter_is_in_sample_only": True,
        }
        for params in default_breakout_parameter_grid()
    ]


def _window_return(frame: pl.DataFrame) -> float | None:
    if frame.is_empty() or "equity" not in frame.columns:
        return None
    values = [float(value) for value in frame.get_column("equity").drop_nulls().to_list()]
    if len(values) < 2 or values[0] == 0:
        return None
    return values[-1] / values[0] - 1


def _max_drawdown_from_frame(frame: pl.DataFrame) -> float | None:
    if frame.is_empty() or "equity" not in frame.columns:
        return None
    values = [float(value) for value in frame.get_column("equity").drop_nulls().to_list()]
    if not values:
        return None
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1 if peak else 0.0)
    return max_dd
