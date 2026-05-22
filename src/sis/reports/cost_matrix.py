from __future__ import annotations

from pathlib import Path

import polars as pl


BASE_ROWS = [
    {
        "venue": "gtrade",
        "symbol": "SPY",
        "asset_class": "index",
        "open_fee_bps": 5,
        "close_fee_bps": 5,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "spreadP requires live probe",
    },
    {
        "venue": "gtrade",
        "symbol": "QQQ",
        "asset_class": "index",
        "open_fee_bps": 5,
        "close_fee_bps": 5,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "spreadP requires live probe",
    },
    {
        "venue": "gtrade",
        "symbol": "XAU",
        "asset_class": "commodity",
        "open_fee_bps": 5,
        "close_fee_bps": 5,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "fixed spread 1 bps; holding/borrowing requires live probe",
    },
    {
        "venue": "ostium",
        "symbol": "SPX_EQUIV",
        "asset_class": "index",
        "open_fee_bps": None,
        "close_fee_bps": None,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "requires probe",
    },
    {
        "venue": "ostium",
        "symbol": "NDX_EQUIV",
        "asset_class": "index",
        "open_fee_bps": None,
        "close_fee_bps": None,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "requires probe",
    },
    {
        "venue": "ostium",
        "symbol": "XAU",
        "asset_class": "commodity",
        "open_fee_bps": None,
        "close_fee_bps": None,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "requires probe",
    },
]


def _base_frame() -> pl.DataFrame:
    return pl.DataFrame(BASE_ROWS)


def build_initial_cost_matrix(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _base_frame().write_csv(out_path)


def _quote_aggregates(quotes_path: Path) -> pl.DataFrame | None:
    if not quotes_path.exists():
        return None

    quotes = pl.read_parquet(quotes_path)
    if quotes.is_empty():
        return None

    now_ms = int(__import__("time").time() * 1000)
    with_metrics = quotes.with_columns(
        pl.col("is_tradable").cast(pl.Float64).alias("_tradable"),
        (
            pl.when(pl.col("oracle_ts_ms").is_null())
            .then(None)
            .otherwise(((pl.lit(now_ms) - pl.col("oracle_ts_ms")) > 3000).cast(pl.Float64))
        ).alias("_stale"),
    )

    return (
        with_metrics.group_by(["venue", "canonical_symbol"])
        .agg(
            pl.col("spread_bps").quantile(0.50).alias("spread_p50_bps_live"),
            pl.col("spread_bps").quantile(0.90).alias("spread_p90_bps_live"),
            pl.col("spread_bps").quantile(0.99).alias("spread_p99_bps_live"),
            pl.col("_stale").mean().alias("stale_rate_live"),
            pl.col("_tradable").mean().alias("tradable_rate_live"),
        )
        .rename({"canonical_symbol": "symbol"})
    )


def build_cost_matrix_from_quotes(quotes_path: Path, out_path: Path) -> None:
    base = _base_frame()
    aggregates = _quote_aggregates(quotes_path)
    if aggregates is None:
        build_initial_cost_matrix(out_path)
        return

    matrix = base.join(aggregates, on=["venue", "symbol"], how="left").with_columns(
        pl.coalesce(["spread_p50_bps_live", "spread_p50_bps"]).alias("spread_p50_bps"),
        pl.coalesce(["spread_p90_bps_live", "spread_p90_bps"]).alias("spread_p90_bps"),
        pl.coalesce(["spread_p99_bps_live", "spread_p99_bps"]).alias("spread_p99_bps"),
        pl.coalesce(["stale_rate_live", "stale_rate"]).alias("stale_rate"),
        pl.coalesce(["tradable_rate_live", "tradable_rate"]).alias("tradable_rate"),
    )
    matrix = matrix.drop(
        [
            "spread_p50_bps_live",
            "spread_p90_bps_live",
            "spread_p99_bps_live",
            "stale_rate_live",
            "tradable_rate_live",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_csv(out_path)
