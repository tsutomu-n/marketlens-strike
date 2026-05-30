from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from sis.research.signal_builder import build_signals
from sis.research.strategy_lab.signal_artifact import (
    read_strategy_signal_manifest,
    signal_artifact_run_id,
)


def _feature_frame() -> pl.DataFrame:
    start_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[dict] = []
    for day_index in range(8):
        rows.append(
            {
                "ts": start_ts + timedelta(days=day_index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "is_event_blackout": False,
                "close_above_sma20": True,
                "research_return_1d": 0.01,
                "t10y2y": 1.0,
                "vix_level": 20.0,
                "source_confidence": 0.75,
                "venue_quality_score": 0.8,
            }
        )
    return pl.DataFrame(rows)


def _sp500_feature_frame() -> pl.DataFrame:
    start_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[dict] = []
    for day_index in range(8):
        rows.append(
            {
                "ts": start_ts + timedelta(days=day_index),
                "canonical_symbol": "SPY",
                "trade_allowed": True,
                "is_event_blackout": False,
                "close_above_sma20": True,
                "research_return_1d": 0.01,
                "t10y2y": 1.0,
                "vix_level": 20.0,
                "source_confidence": 0.75,
                "venue_quality_score": 0.8,
            }
        )
    return pl.DataFrame(rows)


def test_build_signals_writes_canonical_strategy_signal_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    _feature_frame().write_parquet(feature_panel_path)

    legacy_csv_path = build_signals(data_dir)
    parquet_path = data_dir / "research/strategy_signals.parquet"
    jsonl_path = data_dir / "research/strategy_signals.jsonl"
    manifest_path = data_dir / "research/strategy_signal_manifest.json"

    assert legacy_csv_path == data_dir / "research/signals.csv"
    assert legacy_csv_path.exists()
    assert parquet_path.exists()
    assert jsonl_path.exists()
    assert manifest_path.exists()

    signals = pl.read_parquet(parquet_path)
    manifest = read_strategy_signal_manifest(manifest_path)
    assert {
        "schema_version",
        "signal_id",
        "strategy_id",
        "strategy_family",
        "strategy_version",
        "execution_venue",
        "execution_symbol",
        "real_market_symbol",
        "rank_score",
        "tail_bucket",
        "source_confidence",
        "venue_quality_score",
    }.issubset(set(signals.columns))
    assert set(signals.get_column("execution_symbol").to_list()) == {"XYZ100"}
    assert set(signals.get_column("real_market_symbol").to_list()) == {"QQQ"}
    assert set(signals.get_column("source_confidence").to_list()) == {0.75}
    assert set(signals.get_column("venue_quality_score").to_list()) == {0.8}
    assert manifest.generator_id == "qqq_trend_rates_vix"
    assert manifest.strategy_id == "equity_index_momentum_v0"
    assert manifest.signal_count == signals.height


def test_legacy_signals_csv_is_thin_export(tmp_path) -> None:
    data_dir = tmp_path / "data"
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    _feature_frame().write_parquet(feature_panel_path)

    legacy_csv_path = build_signals(data_dir)

    legacy = pl.read_csv(legacy_csv_path, try_parse_dates=True)
    assert set(legacy.columns) == {
        "ts_signal",
        "canonical_symbol",
        "side",
        "timeframe",
        "signal_strength",
        "strategy_name",
        "reason",
    }
    assert set(legacy.get_column("canonical_symbol").to_list()) == {"XYZ100"}


def test_build_signals_can_run_sp500_generator(tmp_path) -> None:
    data_dir = tmp_path / "data"
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    _sp500_feature_frame().write_parquet(feature_panel_path)

    build_signals(data_dir, generator_id="sp500_trend_rates_vix")

    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert set(signals.get_column("strategy_id").to_list()) == {"sp500_index_momentum_v0"}
    assert set(signals.get_column("execution_symbol").to_list()) == {"SP500"}
    assert set(signals.get_column("real_market_symbol").to_list()) == {"SPY"}
    assert set(signals.get_column("source_confidence").to_list()) == {0.75}
    assert set(signals.get_column("venue_quality_score").to_list()) == {0.8}


def test_build_signals_writes_manifest_and_schema_for_no_signal_artifact(tmp_path) -> None:
    data_dir = tmp_path / "data"
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    _feature_frame().with_columns(pl.lit(False).alias("trade_allowed")).write_parquet(
        feature_panel_path
    )

    build_signals(data_dir)

    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    manifest = read_strategy_signal_manifest(data_dir / "research/strategy_signal_manifest.json")
    assert signals.height == 0
    assert {
        "schema_version",
        "signal_id",
        "strategy_id",
        "strategy_family",
        "strategy_version",
        "execution_venue",
        "execution_symbol",
        "real_market_symbol",
        "source_confidence",
        "venue_quality_score",
    }.issubset(set(signals.columns))
    assert manifest.generator_id == "qqq_trend_rates_vix"
    assert manifest.strategy_id == "equity_index_momentum_v0"
    assert manifest.signal_count == 0
    assert manifest.signal_artifact_run_id


def test_no_signal_run_id_differs_by_generator(tmp_path) -> None:
    qqq_data_dir = tmp_path / "qqq"
    sp500_data_dir = tmp_path / "sp500"
    for data_dir, frame in (
        (qqq_data_dir, _feature_frame().with_columns(pl.lit(False).alias("trade_allowed"))),
        (sp500_data_dir, _sp500_feature_frame().with_columns(pl.lit(False).alias("trade_allowed"))),
    ):
        feature_panel_path = data_dir / "research/feature_panel.parquet"
        feature_panel_path.parent.mkdir(parents=True)
        frame.write_parquet(feature_panel_path)

    build_signals(qqq_data_dir)
    build_signals(sp500_data_dir, generator_id="sp500_trend_rates_vix")

    qqq_manifest = read_strategy_signal_manifest(
        qqq_data_dir / "research/strategy_signal_manifest.json"
    )
    sp500_manifest = read_strategy_signal_manifest(
        sp500_data_dir / "research/strategy_signal_manifest.json"
    )
    assert qqq_manifest.signal_artifact_run_id != sp500_manifest.signal_artifact_run_id


def test_signal_run_id_uses_quality_but_not_generated_at(tmp_path) -> None:
    data_dir = tmp_path / "data"
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    _feature_frame().write_parquet(feature_panel_path)
    build_signals(data_dir)

    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    original_run_id = signal_artifact_run_id(signals)

    generated_at_changed = signals.with_columns(
        (pl.col("generated_at") + pl.duration(seconds=30)).alias("generated_at")
    )
    assert signal_artifact_run_id(generated_at_changed) == original_run_id

    quality_changed = signals.with_columns(pl.lit(0.55).alias("source_confidence"))
    assert signal_artifact_run_id(quality_changed) != original_run_id


def test_build_signals_fails_closed_for_unknown_generator(tmp_path) -> None:
    data_dir = tmp_path / "data"
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    _feature_frame().write_parquet(feature_panel_path)

    with pytest.raises(KeyError, match="unknown_generator"):
        build_signals(data_dir, generator_id="unknown_generator")
