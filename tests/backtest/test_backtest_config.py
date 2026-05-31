from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig


def test_backtest_config_normalizes_symbol_and_accepts_rev3_defaults() -> None:
    config = BacktestConfig(
        run_id="run-001",
        strategy_id="sp500_breakout_v0",
        symbol=" sp500 ",
        timeframe="1h",
        period=PeriodConfig(
            warmup_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_start_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )

    assert config.schema_version == "trade_xyz_backtest_config.v1"
    assert config.symbol == "SP500"
    assert config.execution.side_mode == "long_only"
    assert config.execution.fill_model == "market_like_taker_v0"
    assert config.cost.fee_model_ref == "configs/fee_model.trade_xyz.yaml"
    assert config.cost.funding_policy == "nullable_zero_v0"
    assert config.leverage.mode == "disabled"


def test_backtest_config_requires_evaluation_start_before_end() -> None:
    with pytest.raises(ValidationError, match="evaluation_start_ts must be < evaluation_end_ts"):
        BacktestConfig(
            run_id="run-001",
            strategy_id="sp500_breakout_v0",
            symbol="SP500",
            timeframe="1h",
            period=PeriodConfig(
                evaluation_start_ts=datetime(2026, 1, 3, tzinfo=timezone.utc),
                evaluation_end_ts=datetime(2026, 1, 3, tzinfo=timezone.utc),
            ),
            initial_cash_usd=10_000,
            position_sizing=PositionSizingConfig(notional_usd=1_000),
        )


def test_backtest_config_rejects_warmup_after_evaluation_start() -> None:
    with pytest.raises(ValidationError, match="warmup_start_ts must be <= evaluation_start_ts"):
        BacktestConfig(
            run_id="run-001",
            strategy_id="sp500_breakout_v0",
            symbol="SP500",
            timeframe="1h",
            period=PeriodConfig(
                warmup_start_ts=datetime(2026, 1, 2, 1, tzinfo=timezone.utc),
                evaluation_start_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
                evaluation_end_ts=datetime(2026, 1, 3, tzinfo=timezone.utc),
            ),
            initial_cash_usd=10_000,
            position_sizing=PositionSizingConfig(notional_usd=1_000),
        )


def test_position_sizing_rejects_notional_above_maximum() -> None:
    with pytest.raises(ValidationError, match="notional_usd must be <= max_position_notional_usd"):
        PositionSizingConfig(notional_usd=2_000, max_position_notional_usd=1_000)
