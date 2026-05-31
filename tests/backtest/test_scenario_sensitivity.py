from __future__ import annotations

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.scenarios import default_scenarios
from datetime import datetime, timezone


def test_default_scenarios_include_rev3_set() -> None:
    config = BacktestConfig(
        run_id="run-001",
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

    scenarios = default_scenarios(config)

    assert [scenario.name for scenario in scenarios] == [
        "base",
        "fee_2x",
        "slippage_5bps",
        "conservative",
    ]
    assert scenarios[-1].config.cost.fee_multiplier == 2.0
    assert scenarios[-1].config.execution.extra_slippage_bps == 10
