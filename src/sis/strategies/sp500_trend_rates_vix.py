from __future__ import annotations

import polars as pl


def build_sp500_trend_rates_vix_signals(feature_frame: pl.DataFrame) -> pl.DataFrame:
    if feature_frame.is_empty():
        return pl.DataFrame(
            schema={
                "ts_signal": pl.Datetime(time_zone="UTC"),
                "canonical_symbol": pl.Utf8,
                "side": pl.Utf8,
                "timeframe": pl.Utf8,
                "signal_strength": pl.Float64,
                "strategy_name": pl.Utf8,
                "reason": pl.Utf8,
            }
        )

    return (
        feature_frame.filter(pl.col("canonical_symbol") == "SPY")
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
            pl.lit("sp500_trend_rates_vix").alias("strategy_name"),
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
