from __future__ import annotations

import polars as pl

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.run_loop import row_event_ts


def build_funding_event_rows(
    events: pl.DataFrame | None, *, config: BacktestConfig
) -> list[dict[str, object]]:
    return [
        row
        for row in _normalize_funding_events(events, symbol=config.symbol)
        if config.period.evaluation_start_ts <= row_event_ts(row) < config.period.evaluation_end_ts
    ]


def _normalize_funding_events(
    events: pl.DataFrame | None, *, symbol: str
) -> list[dict[str, object]]:
    if events is None or events.is_empty():
        return []
    if "funding_event_ts" not in events.columns:
        raise ValueError("funding_events missing required column: funding_event_ts")
    symbol_column = "canonical_symbol" if "canonical_symbol" in events.columns else "symbol"
    if symbol_column not in events.columns:
        raise ValueError("funding_events missing symbol column: canonical_symbol or symbol")
    required = {"funding_rate", "oracle_price_at_funding"}
    missing = sorted(required - set(events.columns))
    if missing:
        raise ValueError(f"funding_events missing required columns: {', '.join(missing)}")

    normalized = events.with_columns(
        [
            pl.col(symbol_column)
            .cast(pl.Utf8)
            .str.strip_chars()
            .str.to_uppercase()
            .alias("_symbol"),
            pl.col("funding_event_ts")
            .str.to_datetime(time_zone="UTC", strict=False)
            .alias("event_ts")
            if events.schema["funding_event_ts"] == pl.Utf8
            else pl.col("funding_event_ts").alias("event_ts"),
            pl.col("funding_rate").cast(pl.Float64),
            pl.col("oracle_price_at_funding").cast(pl.Float64).alias("oracle_price"),
        ]
    ).filter(pl.col("_symbol") == symbol.strip().upper())
    if normalized.is_empty():
        return []
    return normalized.sort("event_ts").to_dicts()
