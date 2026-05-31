from __future__ import annotations

from datetime import datetime, timezone
import json

import polars as pl

from sis.backtest.engine.config import (
    BacktestConfig,
    CostConfig,
    ExecutionConfig,
    PeriodConfig,
    PositionSizingConfig,
)
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


def test_minimal_runner_writes_core_artifacts_and_uses_next_row_fill(tmp_path) -> None:
    result = run_backtest(
        config=_config(),
        market_data=_frame(),
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    run_dir = tmp_path / "run-001"
    assert result.run_dir == run_dir
    for name in [
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
        "benchmark_equity_curve.parquet",
        "scenario_results.parquet",
        "scenario_summary.json",
        "split_results.json",
        "parameter_results.parquet",
        "parameter_summary.json",
        "candidate_result.json",
        "backtest_report.md",
        "backtest_report.html",
    ]:
        assert (run_dir / name).exists()
    assert (run_dir / "charts/equity_curve.svg").exists()
    assert (run_dir / "charts_data/equity_curve.json").exists()

    fills = pl.read_parquet(run_dir / "fills.parquet")
    assert fills.height == 2
    assert fills.get_column("fee_source").to_list() == ["row", "row"]
    assert fills.get_column("event_ts").to_list() == [
        datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 5, tzinfo=timezone.utc),
    ]
    assert fills.get_column("fill_price_source").to_list() == ["best_ask", "best_bid"]
    assert pl.read_parquet(run_dir / "orders.parquet").height == 2
    assert pl.read_parquet(run_dir / "trades.parquet").height == 1
    scenarios = pl.read_parquet(run_dir / "scenario_results.parquet")
    base = scenarios.filter(pl.col("scenario") == "base").select("net_return_after_cost").item()
    conservative = (
        scenarios.filter(pl.col("scenario") == "conservative")
        .select("net_return_after_cost")
        .item()
    )
    assert conservative < base
    chart_data = json.loads((run_dir / "charts_data/equity_curve.json").read_text(encoding="utf-8"))
    assert chart_data["rows"]
    assert "equity" in chart_data["rows"][0]
    assert "<polyline" in (run_dir / "charts/equity_curve.svg").read_text(encoding="utf-8")


def test_runner_force_closes_open_position_on_end_when_enabled(tmp_path) -> None:
    config = _config().model_copy(
        update={"run_id": "force-close", "execution": ExecutionConfig(force_close_on_end=True)}
    )
    result = run_backtest(
        config=config,
        market_data=_frame().slice(0, 4),
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    trades = pl.read_parquet(result.run_dir / "trades.parquet")
    assert trades.height == 1
    assert trades.get_column("exit_reason").to_list() == ["forced_end_close"]


def test_runner_applies_fixture_hourly_funding_only_on_funding_event(tmp_path) -> None:
    config = _config().model_copy(
        update={
            "run_id": "funding-run",
            "cost": CostConfig(funding_policy="fixture_hourly_v0"),
            "execution": ExecutionConfig(force_close_on_end=True),
        }
    )
    frame = _frame().with_columns(
        [
            pl.Series("oracle_price", [100.0] * 6),
            pl.Series("funding_rate", [None, None, None, 0.01, 0.01, 0.01]),
            pl.Series("is_funding_event", [False, False, False, True, False, True]),
        ]
    )

    result = run_backtest(
        config=config,
        market_data=frame,
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    metrics = json.loads((result.run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["funding_impact"] < 0
    assert metrics["blocked_reason_counts"] == {}


def test_runner_applies_external_funding_events_without_using_quote_row_funding(
    tmp_path,
) -> None:
    config = _config().model_copy(
        update={
            "run_id": "external-funding-run",
            "cost": CostConfig(funding_policy="fixture_hourly_v0"),
            "execution": ExecutionConfig(force_close_on_end=True),
        }
    )
    frame = _frame().with_columns(
        [
            pl.Series("oracle_price", [100.0] * 6),
            pl.Series("funding_rate", [0.99] * 6),
            pl.Series("funding_interval_minutes", [60] * 6),
            pl.Series("is_funding_event", [False] * 6),
        ]
    )
    funding_events = pl.DataFrame(
        {
            "funding_event_ts": [datetime(2026, 1, 1, 3, tzinfo=timezone.utc)],
            "canonical_symbol": ["SP500"],
            "funding_rate": [0.01],
            "funding_interval_minutes": [60],
            "oracle_price_at_funding": [100.0],
            "raw_payload_ref": ["fixture://funding#row=0"],
        }
    )

    result = run_backtest(
        config=config,
        market_data=frame,
        funding_events=funding_events,
        funding_events_ref="fixture://funding",
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    metrics = json.loads((result.run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["funding_event_count"] == 1
    assert metrics["funding_events_ref"] == "fixture://funding"
    assert -20 < metrics["funding_impact"] < 0
    assert metrics["blocked_reason_counts"] == {}


def test_runner_records_nullable_zero_funding_warning_when_runtime_rate_is_present(
    tmp_path,
) -> None:
    config = _config().model_copy(
        update={
            "run_id": "nullable-funding-warning",
            "execution": ExecutionConfig(force_close_on_end=True),
        }
    )
    frame = _frame().with_columns(
        [
            pl.Series("oracle_price", [100.0] * 6),
            pl.Series("funding_rate", [None, None, None, 0.01, 0.01, 0.01]),
            pl.Series("funding_interval_minutes", [None] * 6),
        ]
    )

    result = run_backtest(
        config=config,
        market_data=frame,
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    metrics = json.loads((result.run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["funding_impact"] == 0
    assert metrics["blocked_reason_counts"] == {
        "funding_rate_present_without_interval_assertion": 1
    }


def test_runner_applies_fee_multiplier_to_real_fills(tmp_path) -> None:
    base = run_backtest(
        config=_config().model_copy(update={"run_id": "fee-base"}),
        market_data=_frame(),
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )
    doubled = run_backtest(
        config=_config().model_copy(
            update={
                "run_id": "fee-doubled",
                "cost": CostConfig(fee_multiplier=2.0),
            }
        ),
        market_data=_frame(),
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    base_fills = pl.read_parquet(base.run_dir / "fills.parquet")
    doubled_fills = pl.read_parquet(doubled.run_dir / "fills.parquet")
    assert doubled_fills.get_column("fee_bps").to_list() == [18.0, 18.0]
    assert (
        doubled_fills.get_column("fee_amount").sum()
        == base_fills.get_column("fee_amount").sum() * 2
    )


def test_runner_blocks_last_row_signal_without_future_fill_row(tmp_path) -> None:
    frame = _frame().with_columns(pl.Series("close", [100.0, 99.0, 98.0, 97.0, 96.0, 120.0]))
    result = run_backtest(
        config=_config().model_copy(update={"run_id": "last-row-signal"}),
        market_data=frame,
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    blocked = pl.read_parquet(result.run_dir / "blocked_events.parquet")
    assert blocked.get_column("reason").to_list() == ["no_future_fill_row"]
    assert pl.read_parquet(result.run_dir / "fills.parquet").is_empty()
