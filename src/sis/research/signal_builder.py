from __future__ import annotations

from pathlib import Path

import polars as pl


def build_signals(data_dir: Path) -> Path:
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    if not feature_panel_path.exists():
        raise FileNotFoundError(f"Research feature panel not found: {feature_panel_path}")

    frame = pl.read_parquet(feature_panel_path)
    if frame.is_empty():
        raise ValueError("Feature panel is empty.")

    signals = (
        frame.filter(pl.col("canonical_symbol") == "QQQ")
        .filter(pl.col("trade_allowed"))
        .filter(~pl.col("is_event_blackout"))
        .filter(pl.col("close_above_sma20"))
        .with_columns(
            pl.col("ts").alias("ts_signal"),
            pl.lit("long").alias("side"),
            pl.lit("4h").alias("timeframe"),
            (
                (pl.col("research_return_1d").fill_null(0.0) * 100.0)
                + (pl.col("t10y2y").fill_null(0.0) * 0.01)
                - (pl.col("vix_level").fill_null(0.0) * 0.001)
            ).alias("signal_strength"),
            pl.lit("qqq_trend_rates_vix_seed").alias("strategy_name"),
            pl.lit("close_above_sma20_and_trade_allowed").alias("reason"),
        )
        .select(
            "ts_signal",
            "canonical_symbol",
            "side",
            "timeframe",
            "signal_strength",
            "strategy_name",
            "reason",
        )
        .sort("ts_signal")
    )

    out = data_dir / "research/signals.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    signals.write_csv(out)
    return out
