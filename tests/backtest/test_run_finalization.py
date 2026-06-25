from __future__ import annotations

from datetime import datetime, timezone
import json

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.data_quality import apply_period_filter, evaluate_data_quality
from sis.backtest.engine.manifest import build_data_manifest
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_finalization import finalize_backtest_run
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.engine.run_outputs import build_run_outputs
from sis.backtest.trade_xyz.schema import normalize_trade_xyz_market_data


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="finalization-run",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )


def _normalized_frame() -> pl.DataFrame:
    return normalize_trade_xyz_market_data(
        pl.DataFrame(
            {
                "event_ts": [
                    datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
                ],
                "symbol": ["SP500", "SP500", "SP500"],
                "close": [100.0, 101.0, 102.0],
                "best_bid": [99.0, 100.0, 101.0],
                "best_ask": [100.0, 101.0, 102.0],
                "taker_fee_bps": [9.0, 9.0, 9.0],
                "maker_fee_bps": [3.0, 3.0, 3.0],
                "market_status": ["open", "open", "open"],
                "is_tradable": [True, True, True],
                "block_reasons": [[], [], []],
            }
        ),
        symbol="SP500",
    )


def test_finalize_backtest_run_writes_result_and_artifact_outputs(tmp_path) -> None:
    config = _config()
    normalized = _normalized_frame()
    filtered = apply_period_filter(normalized, config=config).with_row_index("_row_index")
    quality = evaluate_data_quality(
        normalized,
        config=config,
        input_row_count=normalized.height,
        required_min_bars=0,
    )
    manifest = build_data_manifest(
        config=config,
        frame=normalized,
        input_data_ref="fixture://sp500",
        data_quality=quality,
        event_time_source="event_ts",
        close_source="close",
        bar_builder=None,
    )
    equity_rows = [
        {
            "event_ts": row["event_ts"],
            "cash_usd": 10_000.0 + offset,
            "position_qty": 0.0,
            "equity": 10_000.0 + offset,
            "unrealized_pnl": 0.0,
            "funding_pnl": 0.0,
            "is_evaluation": row["is_evaluation"],
            "session_type": "unknown",
            "market_status": row["market_status"],
        }
        for offset, row in enumerate(filtered.to_dicts())
    ]
    outputs = build_run_outputs(
        initial_cash_usd=config.initial_cash_usd,
        orders=[],
        fills=[],
        trades=[],
        blocked=[],
        equity_rows=equity_rows,
        portfolio=Portfolio.flat(initial_cash_usd=config.initial_cash_usd),
        end_position_policy=config.execution.end_position_policy,
        funding_events_ref=None,
        funding_event_count=0,
    )

    run_dir = finalize_backtest_run(
        config=config,
        normalized=normalized,
        filtered=filtered,
        out_dir=tmp_path,
        input_data_ref="fixture://sp500",
        data_quality=quality,
        data_manifest=manifest,
        event_time_source="event_ts",
        close_source="close",
        outputs=outputs,
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    assert run_dir == tmp_path / "finalization-run"
    assert (run_dir / "benchmark_results.json").exists()
    assert (run_dir / "benchmark_equity_curve.parquet").exists()
    assert (run_dir / "scenario_results.parquet").exists()
    assert (run_dir / "split_results.json").exists()
    assert (run_dir / "parameter_results.parquet").exists()
    assert (run_dir / "candidate_result.json").exists()
    assert (run_dir / "backtest_report.md").exists()
    assert pl.read_parquet(run_dir / "scenario_results.parquet").height == 4
    assert pl.read_parquet(run_dir / "parameter_results.parquet").height == 9
    split = json.loads((run_dir / "split_results.json").read_text(encoding="utf-8"))
    assert split["oos_validation_done"] is True
    run_meta = json.loads((run_dir / "backtest_run.json").read_text(encoding="utf-8"))
    assert run_meta["no_live_order"] is True
    assert run_meta["wallet_used"] is False
    assert run_meta["exchange_write_used"] is False
