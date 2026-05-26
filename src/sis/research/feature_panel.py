from __future__ import annotations

from pathlib import Path

import polars as pl


def _load_event_calendar(path: Path) -> pl.DataFrame:
    if not path.exists():
        return pl.DataFrame(
            schema={
                "event_ts": pl.Datetime(time_zone="UTC"),
                "event_name": pl.Utf8,
                "event_class": pl.Utf8,
                "importance": pl.Utf8,
                "before_minutes": pl.Int64,
                "after_minutes": pl.Int64,
                "action": pl.Utf8,
            }
        )
    return pl.read_parquet(path)


def _pivot_macro(frame: pl.DataFrame) -> pl.DataFrame:
    if frame.is_empty():
        return pl.DataFrame(schema={"date": pl.Date})
    pivoted = frame.pivot(on="series_id", index="date", values="value", aggregate_function="first")
    rename_map = {
        "DGS10": "dgs10",
        "DGS2": "dgs2",
        "T10Y2Y": "t10y2y",
        "FEDFUNDS": "fedfunds",
    }
    available = {key: value for key, value in rename_map.items() if key in pivoted.columns}
    return pivoted.rename(available)


def build_feature_panel(data_dir: Path) -> Path:
    market_panel_path = data_dir / "research/market_panel.parquet"
    macro_panel_path = data_dir / "research/macro_panel.parquet"
    event_calendar_path = data_dir / "research/event_calendar.parquet"
    if not market_panel_path.exists():
        raise FileNotFoundError(f"Research market panel not found: {market_panel_path}")
    if not macro_panel_path.exists():
        raise FileNotFoundError(f"Research macro panel not found: {macro_panel_path}")

    market = pl.read_parquet(market_panel_path).sort(["symbol", "ts"])
    macro = _pivot_macro(pl.read_parquet(macro_panel_path))
    events = _load_event_calendar(event_calendar_path)

    event_windows: list[tuple] = []
    for row in events.to_dicts():
        event_ts = row["event_ts"]
        before_minutes = int(row["before_minutes"])
        after_minutes = int(row["after_minutes"])
        event_windows.append((event_ts, before_minutes, after_minutes))

    feature = market.with_columns(
        pl.col("symbol").alias("canonical_symbol"),
        pl.col("close").alias("research_close"),
        pl.col("ts").dt.date().alias("date"),
        pl.col("close").pct_change().over("symbol").alias("research_return_1d"),
        (pl.col("close") / pl.col("close").shift(3).over("symbol") - 1.0).alias(
            "research_return_4h"
        ),
        (pl.col("close") / pl.col("close").shift(5).over("symbol") - 1.0).alias(
            "research_return_3d"
        ),
        pl.col("close").rolling_mean(window_size=20, min_samples=5).over("symbol").alias("sma_20"),
        pl.col("close").rolling_mean(window_size=50, min_samples=10).over("symbol").alias("sma_50"),
        pl.col("close")
        .rolling_std(window_size=20, min_samples=5)
        .over("symbol")
        .alias("realized_vol_20"),
    ).join(macro, on="date", how="left")

    symbols = set(market.get_column("symbol").to_list())
    if "^VIX" in symbols:
        vix_proxy = market.filter(pl.col("symbol") == "^VIX").select(
            ["ts", pl.col("close").alias("vix_level")]
        )
        feature = feature.join(vix_proxy, on="ts", how="left")
    else:
        feature = feature.with_columns(pl.lit(None).cast(pl.Float64).alias("vix_level"))

    if "UUP" in symbols:
        dxy_proxy = market.filter(pl.col("symbol") == "UUP").select(
            ["ts", pl.col("close").alias("dxy_proxy")]
        )
        feature = feature.join(dxy_proxy, on="ts", how="left")
    else:
        feature = feature.with_columns(pl.lit(None).cast(pl.Float64).alias("dxy_proxy"))

    feature = feature.with_columns(
        (pl.col("research_close") > pl.col("sma_20")).alias("close_above_sma20")
    )

    if event_windows:
        is_blackout: list[bool] = []
        minutes_to_next: list[int | None] = []
        minutes_since_last: list[int | None] = []
        for ts in feature.get_column("ts").to_list():
            deltas = [int((event_ts - ts).total_seconds() / 60) for event_ts, _, _ in event_windows]
            next_delta = min((delta for delta in deltas if delta >= 0), default=None)
            prev_delta = min((-delta for delta in deltas if delta <= 0), default=None)
            blocked = False
            for event_ts, before_minutes, after_minutes in event_windows:
                delta_minutes = (event_ts - ts).total_seconds() / 60
                if -after_minutes <= delta_minutes <= before_minutes:
                    blocked = True
                    break
            is_blackout.append(blocked)
            minutes_to_next.append(next_delta)
            minutes_since_last.append(prev_delta)
        feature = feature.with_columns(
            pl.Series("is_event_blackout", is_blackout),
            pl.Series("minutes_to_next_event", minutes_to_next, dtype=pl.Int64),
            pl.Series("minutes_since_last_event", minutes_since_last, dtype=pl.Int64),
        )
    else:
        feature = feature.with_columns(
            pl.lit(False).alias("is_event_blackout"),
            pl.lit(None).cast(pl.Int64).alias("minutes_to_next_event"),
            pl.lit(None).cast(pl.Int64).alias("minutes_since_last_event"),
        )

    feature = feature.with_columns(
        pl.lit("research").alias("venue"),
        pl.lit(None).cast(pl.Float64).alias("venue_mark_price"),
        pl.lit(None).cast(pl.Float64).alias("venue_index_price"),
        pl.lit(None).cast(pl.Float64).alias("venue_spread_bps"),
        pl.lit(None).cast(pl.Float64).alias("venue_stale_rate"),
        pl.lit(None).cast(pl.Float64).alias("venue_tradable_rate"),
        (~pl.col("is_event_blackout")).alias("trade_allowed"),
        pl.when(pl.col("is_event_blackout"))
        .then(pl.lit("EVENT_BLACKOUT"))
        .otherwise(pl.lit(None))
        .alias("blocked_reason"),
    )

    for column in ("dgs10", "dgs2", "t10y2y", "fedfunds", "vix_level", "dxy_proxy"):
        if column not in feature.columns:
            feature = feature.with_columns(pl.lit(None).cast(pl.Float64).alias(column))

    out = data_dir / "research/feature_panel.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    feature.select(
        "ts",
        "canonical_symbol",
        "research_close",
        "research_return_4h",
        "research_return_1d",
        "research_return_3d",
        "sma_20",
        "sma_50",
        "close_above_sma20",
        "realized_vol_20",
        "dgs10",
        "dgs2",
        "t10y2y",
        "vix_level",
        "dxy_proxy",
        "is_event_blackout",
        "minutes_to_next_event",
        "minutes_since_last_event",
        "venue",
        "venue_mark_price",
        "venue_index_price",
        "venue_spread_bps",
        "venue_stale_rate",
        "venue_tradable_rate",
        "trade_allowed",
        "blocked_reason",
    ).sort(["canonical_symbol", "ts"]).write_parquet(out)
    return out
