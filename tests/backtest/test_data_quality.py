from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.data_quality import evaluate_data_quality
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
                "event_ts": [
                    datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                ],
                "symbol": ["SP500", "SP500"],
                "mid_price": [100.0, 101.0],
                "best_bid": [99.9, 100.9],
                "best_ask": [100.1, 101.1],
                "taker_fee_bps": [9.0, 9.0],
                "maker_fee_bps": [3.0, 3.0],
                "is_tradable": [True, True],
                "block_reasons": [[], []],
            }
        ),
        symbol="SP500",
    )


def test_evaluate_data_quality_passes_clean_frame() -> None:
    report = evaluate_data_quality(_frame(), config=_config(), input_row_count=2)

    assert report.status == "pass"
    assert report.input_row_count == 2
    assert report.filtered_row_count == 2
    assert report.duplicate_ts_count == 0
    assert report.out_of_order_count == 0
    assert report.invalid_price_count == 0
    assert report.bid_ask_cross_count == 0
    assert report.errors == []


def test_evaluate_data_quality_fails_missing_required_column() -> None:
    frame = _frame().drop("is_tradable")

    report = evaluate_data_quality(frame, config=_config(), input_row_count=2)

    assert report.status == "fail"
    assert "missing required columns: is_tradable" in report.errors


def test_evaluate_data_quality_warns_duplicate_and_gap() -> None:
    frame = normalize_trade_xyz_market_data(
        pl.DataFrame(
            {
                "event_ts": [
                    datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 5, tzinfo=timezone.utc),
                ],
                "symbol": ["SP500", "SP500", "SP500", "SP500"],
                "mid_price": [100.0, 100.1, 100.5, 101.0],
                "spread_bps": [1.0, 1.0, 1.0, 1.0],
                "fee_mode": ["standard", "standard", "standard", "standard"],
                "is_tradable": [True, True, True, True],
                "block_reasons": [[], [], [], []],
            }
        ),
        symbol="SP500",
    )

    report = evaluate_data_quality(frame, config=_config(), input_row_count=3)

    assert report.status == "warn"
    assert report.duplicate_ts_count == 1
    assert report.cadence_gap_count == 1
    assert "duplicate event_ts per symbol detected" in report.warnings


def test_evaluate_data_quality_surfaces_unresolved_fee_and_funding_assertion_risk() -> None:
    frame = normalize_trade_xyz_market_data(
        pl.DataFrame(
            {
                "event_ts": [
                    datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                ],
                "symbol": ["SP500", "SP500"],
                "mid_price": [100.0, 101.0],
                "spread_bps": [1.0, 1.0],
                "fee_mode": ["unknown", "standard"],
                "taker_fee_bps": [None, 9.0],
                "maker_fee_bps": [None, 3.0],
                "funding_rate": [0.001, 0.001],
                "funding_interval_minutes": [None, None],
                "is_tradable": [True, True],
                "block_reasons": [[], []],
            }
        ),
        symbol="SP500",
    )

    report = evaluate_data_quality(frame, config=_config(), input_row_count=2)

    assert report.status == "warn"
    assert report.unknown_fee_mode_count == 1
    assert report.null_taker_fee_count == 1
    assert report.null_maker_fee_count == 1
    assert report.funding_rate_without_interval_count == 2


def test_evaluate_data_quality_records_operational_missing_rates() -> None:
    report = evaluate_data_quality(_frame(), config=_config(), input_row_count=2)

    assert report.raw_payload_ref_missing_rate == 1.0
    assert report.oracle_ts_missing_rate == 1.0
    assert report.funding_interval_missing_rate == 1.0
    assert report.fee_unresolved_rate == 0.0
    assert report.missing_rate_by_field["raw_payload_ref"] == 1.0
