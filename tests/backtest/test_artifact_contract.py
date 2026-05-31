from __future__ import annotations

import json
from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.runner import BreakoutParameters, run_backtest


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="run-001",
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
            "event_ts": [datetime(2026, 1, 1, hour, tzinfo=timezone.utc) for hour in range(6)],
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


def test_runner_artifacts_satisfy_rev3_metadata_and_quality_contract(tmp_path) -> None:
    result = run_backtest(
        config=_config(),
        market_data=_frame(),
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )
    run_dir = result.run_dir
    required = [
        "backtest_run.json",
        "config.json",
        "config_hash.txt",
        "data_manifest.json",
        "input_schema_hash.txt",
        "data_quality.json",
        "orders.parquet",
        "fills.parquet",
        "trades.parquet",
        "blocked_events.parquet",
        "equity_curve.parquet",
        "metrics.json",
        "benchmark_results.json",
        "scenario_results.parquet",
        "split_results.json",
        "parameter_results.parquet",
        "candidate_result.json",
        "backtest_report.md",
        "backtest_report.html",
    ]
    assert all((run_dir / name).exists() for name in required)

    run_meta = json.loads((run_dir / "backtest_run.json").read_text(encoding="utf-8"))
    assert run_meta["funding_policy"] == "nullable_zero_v0"
    assert run_meta["fill_model"] == "market_like_taker_v0"
    assert run_meta["fee_model_ref"] == "configs/fee_model.trade_xyz.yaml"
    assert run_meta["leverage_mode"] == "disabled"
    assert run_meta["no_live_order"] is True
    assert run_meta["wallet_used"] is False
    assert run_meta["exchange_write_used"] is False

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert "blocked_reason_counts" in metrics
    assert "funding_impact" in metrics
    assert "fee_impact" in metrics
    assert "fee_source_counts" in metrics
    assert metrics["fee_row_resolved_rate"] == 1.0
    assert metrics["fee_config_fallback_rate"] == 0.0
    assert "slippage_impact" in metrics
    assert "session_breakdown" in metrics
    assert "market_status_breakdown" in metrics

    split = json.loads((run_dir / "split_results.json").read_text(encoding="utf-8"))
    assert split["oos_validation_done"] is True
    assert split["train_return"] is not None
    assert split["test_return"] is not None

    parameters = pl.read_parquet(run_dir / "parameter_results.parquet")
    assert "net_return_after_cost" in parameters.columns
    assert parameters.height == 9

    fills = pl.read_parquet(run_dir / "fills.parquet")
    assert fills.get_column("fill_price_source").null_count() == 0
    assert fills.get_column("fee_source").to_list() == ["row", "row"]

    report = (run_dir / "backtest_report.md").read_text(encoding="utf-8")
    assert "blocked_reason_counts" in report
    assert "fee_source_counts" in report
    assert "best_parameter_is_in_sample_only: true" in report
