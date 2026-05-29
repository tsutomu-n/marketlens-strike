from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl

from sis.research.signal_builder import build_signals


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


def test_build_signals_writes_canonical_strategy_signal_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    _feature_frame().write_parquet(feature_panel_path)

    legacy_csv_path = build_signals(data_dir)
    parquet_path = data_dir / "research/strategy_signals.parquet"
    jsonl_path = data_dir / "research/strategy_signals.jsonl"

    assert legacy_csv_path == data_dir / "research/signals.csv"
    assert legacy_csv_path.exists()
    assert parquet_path.exists()
    assert jsonl_path.exists()

    signals = pl.read_parquet(parquet_path)
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
