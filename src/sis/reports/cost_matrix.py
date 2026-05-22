from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.storage.jsonl_store import read_json, read_jsonl


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
    return pl.DataFrame([dict(row) for row in BASE_ROWS])


def _latest_gtrade_sidecar(sidecar_root: Path | None) -> Path | None:
    if sidecar_root is None or not sidecar_root.exists():
        return None
    files = sorted(sidecar_root.glob("*.jsonl"))
    return files[-1] if files else None


def _as_bps_from_gtrade_fee(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value) / 1e8
    except (TypeError, ValueError):
        return None


def _metadata_rows(
    *,
    gtrade_sidecar_root: Path | None = None,
    ostium_registry_path: Path | None = None,
) -> list[dict]:
    rows = [dict(row) for row in BASE_ROWS]
    by_key = {(row["venue"], row["symbol"]): row for row in rows}

    sidecar_path = _latest_gtrade_sidecar(gtrade_sidecar_root)
    if sidecar_path is not None:
        snapshots = list(read_jsonl(sidecar_path))
        if snapshots:
            snapshot = snapshots[-1]
            for pair in snapshot.get("pairs", []):
                symbol = pair.get("canonical_symbol")
                row = by_key.get(("gtrade", symbol))
                if row is None:
                    continue
                spread_bps = pair.get("spread_bps")
                if isinstance(spread_bps, int | float):
                    row["spread_p50_bps"] = float(spread_bps)
                    row["spread_p90_bps"] = float(spread_bps)
                    row["spread_p99_bps"] = float(spread_bps)
                fee_bps = _as_bps_from_gtrade_fee(pair.get("total_position_size_fee_p"))
                if fee_bps is not None:
                    row["open_fee_bps"] = fee_bps
                    row["close_fee_bps"] = fee_bps
                row["notes"] = (
                    f"gTrade sidecar={sidecar_path}; fee_index={pair.get('fee_index')}; "
                    "holding/borrowing requires per-position or fee accrual probe"
                )

    if ostium_registry_path is not None and ostium_registry_path.exists():
        registry = read_json(ostium_registry_path)
        if isinstance(registry, list):
            for item in registry:
                if not isinstance(item, dict) or item.get("venue") != "ostium":
                    continue
                row = by_key.get(("ostium", item.get("canonical_symbol")))
                if row is None:
                    continue
                opening_fee = item.get("opening_fee_bps")
                if isinstance(opening_fee, int | float):
                    row["open_fee_bps"] = float(opening_fee)
                row["notes"] = (
                    f"ostium registry={ostium_registry_path}; "
                    f"rollover_fee_per_block={item.get('rollover_fee_per_block')}; "
                    f"rollover_rate_long={item.get('rollover_rate_long')}; "
                    f"rollover_rate_short={item.get('rollover_rate_short')}; "
                    "holding cost kept null until position/timeframe conversion is verified"
                )

    return rows


def build_initial_cost_matrix(
    out_path: Path,
    *,
    gtrade_sidecar_root: Path | None = None,
    ostium_registry_path: Path | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        _metadata_rows(
            gtrade_sidecar_root=gtrade_sidecar_root,
            ostium_registry_path=ostium_registry_path,
        )
    ).write_csv(out_path)


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


def build_cost_matrix_from_quotes(
    quotes_path: Path,
    out_path: Path,
    *,
    gtrade_sidecar_root: Path | None = None,
    ostium_registry_path: Path | None = None,
) -> None:
    base = pl.DataFrame(
        _metadata_rows(
            gtrade_sidecar_root=gtrade_sidecar_root,
            ostium_registry_path=ostium_registry_path,
        )
    )
    aggregates = _quote_aggregates(quotes_path)
    if aggregates is None:
        build_initial_cost_matrix(
            out_path,
            gtrade_sidecar_root=gtrade_sidecar_root,
            ostium_registry_path=ostium_registry_path,
        )
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
