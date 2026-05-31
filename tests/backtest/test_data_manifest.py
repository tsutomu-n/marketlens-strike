from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.data_quality import evaluate_data_quality
from sis.backtest.engine.hashing import config_hash, frame_sha256, input_schema_hash
from sis.backtest.engine.manifest import build_data_manifest
from sis.backtest.trade_xyz.schema import normalize_trade_xyz_market_data


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="run-001",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            warmup_start_ts=datetime(2025, 12, 31, tzinfo=timezone.utc),
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )


def _frame() -> pl.DataFrame:
    return normalize_trade_xyz_market_data(
        pl.DataFrame(
            {
                "event_ts": [datetime(2026, 1, 1, tzinfo=timezone.utc)],
                "symbol": ["SP500"],
                "mid_price": [100.0],
                "spread_bps": [1.0],
                "fee_mode": ["standard"],
                "is_tradable": [True],
                "block_reasons": [[]],
            }
        ),
        symbol="SP500",
    )


def test_hashes_are_deterministic_and_include_schema() -> None:
    config = _config()
    frame = _frame()

    assert config_hash(config) == config_hash(config)
    assert input_schema_hash(frame) == input_schema_hash(frame)
    assert len(frame_sha256(frame)) == 64
    assert len(config_hash(config)) == 64
    assert len(input_schema_hash(frame)) == 64


def test_build_data_manifest_records_period_hashes_and_quality_summary() -> None:
    config = _config()
    frame = _frame()
    quality = evaluate_data_quality(frame, config=config, input_row_count=1)

    manifest = build_data_manifest(
        config=config,
        frame=frame,
        input_data_ref="fixture://sp500",
        data_quality=quality,
        event_time_source="event_ts",
    )

    assert manifest.schema_version == "trade_xyz_backtest_data_manifest.v1"
    assert manifest.run_id == "run-001"
    assert manifest.input_data_ref == "fixture://sp500"
    assert manifest.input_data_sha256 == frame_sha256(frame)
    assert manifest.input_schema_hash == input_schema_hash(frame)
    assert manifest.config_hash == config_hash(config)
    assert manifest.symbols == ["SP500"]
    assert manifest.filtered_row_count == 1
    assert manifest.data_quality_summary["status"] == "pass"
    assert manifest.data_readiness_summary["raw_payload_ref_missing_rate"] == 1.0
