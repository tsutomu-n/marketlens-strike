from __future__ import annotations

from datetime import datetime
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


def _worst_abs_ostium_rollover_bps(long_rate: object, short_rate: object, hours: float) -> float | None:
    rates: list[float] = []
    for value in (long_rate, short_rate):
        if value in {None, ""}:
            continue
        try:
            rates.append(abs(float(value)))
        except (TypeError, ValueError):
            continue
    if not rates:
        return None
    # Ostium Builder SDK exposes rolloverRate as 8hr percent by side.
    return max(rates) * 100 * (hours / 8)


def _as_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _gtrade_holding_bps(pair: dict, snapshot: dict, hours: float) -> float | None:
    pair_index = pair.get("pair_index")
    if pair_index is None:
        return None
    seconds = hours * 60 * 60
    candidates: list[float] = []

    def indexed(value: object, index: int) -> object | None:
        if isinstance(value, list) and index < len(value):
            return value[index]
        if isinstance(value, dict):
            return value.get(str(index)) or value.get(index)
        return None

    for collateral in snapshot.get("raw", {}).get("collaterals", []):
        if not isinstance(collateral, dict) or collateral.get("isActive") is not True:
            continue
        borrowing_rate_raw = (
            collateral.get("borrowingFees", {})
            .get("v2", {})
            .get("pairParams", [])
        )
        funding_data = collateral.get("fundingFees", {}).get("pairData", [])
        funding_params = collateral.get("fundingFees", {}).get("pairParams", [])
        index = int(pair_index)
        borrow_item = indexed(borrowing_rate_raw, index)
        funding_item = indexed(funding_data, index)
        funding_param = indexed(funding_params, index)

        borrow_bps = 0.0
        if isinstance(borrow_item, dict):
            raw_rate = _as_float(borrow_item.get("borrowingRatePerSecondP"))
            if raw_rate is not None:
                # SDK borrowing v2 precision: raw / 1e10 is percentage per second.
                borrow_bps = raw_rate / 1e10 * seconds * 100

        funding_bps = 0.0
        if (
            isinstance(funding_item, dict)
            and isinstance(funding_param, dict)
            and funding_param.get("fundingFeesEnabled") is True
        ):
            funding_rate = _as_float(funding_item.get("lastFundingRatePerSecondP"))
            if funding_rate is not None:
                # SDK funding precision: raw / 1e18 is fractional rate per second.
                funding_bps = abs(funding_rate / 1e18) * seconds * 10_000

        candidates.append(borrow_bps + funding_bps)

    return max(candidates) if candidates else None


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
                row["holding_cost_4h_bps"] = _gtrade_holding_bps(pair, snapshot, 4)
                row["holding_cost_24h_bps"] = _gtrade_holding_bps(pair, snapshot, 24)
                row["holding_cost_72h_bps"] = _gtrade_holding_bps(pair, snapshot, 72)
                row["notes"] = (
                    f"gTrade sidecar={sidecar_path}; fee_index={pair.get('fee_index')}; "
                    "holding cost uses max active collateral borrowing/funding rate from trading-variables"
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
                row["holding_cost_4h_bps"] = _worst_abs_ostium_rollover_bps(
                    item.get("rollover_rate_long"),
                    item.get("rollover_rate_short"),
                    4,
                )
                row["holding_cost_24h_bps"] = _worst_abs_ostium_rollover_bps(
                    item.get("rollover_rate_long"),
                    item.get("rollover_rate_short"),
                    24,
                )
                row["holding_cost_72h_bps"] = _worst_abs_ostium_rollover_bps(
                    item.get("rollover_rate_long"),
                    item.get("rollover_rate_short"),
                    72,
                )
                row["notes"] = (
                    f"ostium registry={ostium_registry_path}; "
                    f"rollover_fee_per_block={item.get('rollover_fee_per_block')}; "
                    f"rollover_rate_long={item.get('rollover_rate_long')}; "
                    f"rollover_rate_short={item.get('rollover_rate_short')}; "
                    "holding cost uses conservative max(abs(long), abs(short)) 8hr percent conversion"
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

    ts_client_ms = [
        int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
        for value in quotes["ts_client"].to_list()
    ]
    quotes = quotes.with_columns(pl.Series("_ts_client_ms", ts_client_ms))
    with_metrics = quotes.with_columns(
        pl.col("is_tradable").cast(pl.Float64).alias("_tradable"),
    ).with_columns(
        (
            pl.when(pl.col("oracle_ts_ms").is_null())
            .then(None)
            .otherwise(((pl.col("_ts_client_ms") - pl.col("oracle_ts_ms")) > 3000).cast(pl.Float64))
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
