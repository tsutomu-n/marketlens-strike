from __future__ import annotations

from datetime import datetime
from pathlib import Path

import polars as pl

from sis.reports import cost_matrix_metadata
from sis.reports import cost_matrix_navigation
from sis.storage.jsonl_store import write_json


BASE_ROWS = cost_matrix_metadata.BASE_ROWS
_base_frame = cost_matrix_metadata.base_frame
_latest_gtrade_sidecar = cost_matrix_metadata.latest_gtrade_sidecar
_as_bps_from_gtrade_fee = cost_matrix_metadata.as_bps_from_gtrade_fee
_worst_abs_ostium_rollover_bps = cost_matrix_metadata.worst_abs_ostium_rollover_bps
_as_float = cost_matrix_metadata.as_float
_gtrade_holding_bps = cost_matrix_metadata.gtrade_holding_bps
_metadata_rows = cost_matrix_metadata.metadata_rows


def build_initial_cost_matrix(
    out_path: Path,
    *,
    gtrade_sidecar_root: Path | None = None,
    ostium_registry_path: Path | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pl.from_dicts(
        _metadata_rows(
            gtrade_sidecar_root=gtrade_sidecar_root,
            ostium_registry_path=ostium_registry_path,
        ),
        infer_schema_length=None,
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
            .then(1.0)
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
    base = pl.from_dicts(
        _metadata_rows(
            gtrade_sidecar_root=gtrade_sidecar_root,
            ostium_registry_path=ostium_registry_path,
        ),
        infer_schema_length=None,
    )
    aggregates = _quote_aggregates(quotes_path)
    if aggregates is None:
        build_initial_cost_matrix(
            out_path,
            gtrade_sidecar_root=gtrade_sidecar_root,
            ostium_registry_path=ostium_registry_path,
        )
        return

    aggregate_keys = aggregates.select(["venue", "symbol"])
    new_aggregate_rows = (
        aggregates.join(base.select(["venue", "symbol"]), on=["venue", "symbol"], how="anti")
        .with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("asset_class"),
            pl.lit(None, dtype=pl.Float64).alias("open_fee_bps"),
            pl.lit(None, dtype=pl.Float64).alias("close_fee_bps"),
            pl.col("spread_p50_bps_live").alias("spread_p50_bps"),
            pl.col("spread_p90_bps_live").alias("spread_p90_bps"),
            pl.col("spread_p99_bps_live").alias("spread_p99_bps"),
            pl.lit(None, dtype=pl.Float64).alias("holding_cost_4h_bps"),
            pl.lit(None, dtype=pl.Float64).alias("holding_cost_24h_bps"),
            pl.lit(None, dtype=pl.Float64).alias("holding_cost_72h_bps"),
            pl.col("stale_rate_live").alias("stale_rate"),
            pl.col("tradable_rate_live").alias("tradable_rate"),
            pl.lit("derived from normalized quotes").alias("notes"),
        )
        .select(
            [
                "venue",
                "symbol",
                "asset_class",
                "open_fee_bps",
                "close_fee_bps",
                "spread_p50_bps",
                "spread_p90_bps",
                "spread_p99_bps",
                "holding_cost_4h_bps",
                "holding_cost_24h_bps",
                "holding_cost_72h_bps",
                "stale_rate",
                "tradable_rate",
                "notes",
            ]
        )
    )
    matrix = base.join(aggregate_keys, on=["venue", "symbol"], how="semi").join(
        aggregates, on=["venue", "symbol"], how="left"
    )
    matrix = matrix.with_columns(
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
    matrix = pl.concat([matrix, new_aggregate_rows], how="diagonal_relaxed")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_csv(out_path)


_quick_navigation = cost_matrix_navigation.quick_navigation
_related_reports = cost_matrix_navigation.related_reports


def build_cost_matrix_report(
    *,
    cost_matrix_path: Path,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    frame = pl.read_csv(cost_matrix_path) if cost_matrix_path.exists() else pl.DataFrame()
    row_count = frame.height
    venues = (
        sorted(frame.get_column("venue").unique().to_list()) if "venue" in frame.columns else []
    )
    symbols = (
        sorted(frame.get_column("symbol").unique().to_list()) if "symbol" in frame.columns else []
    )
    summary = {
        "row_count": row_count,
        "venues": venues,
        "symbols": symbols,
        "cost_matrix_path": str(cost_matrix_path),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
        "venue_cost_matrix_report_path": str(out_path) if out_path is not None else None,
    }

    lines = ["# Venue Cost Matrix Report", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(
        [
            "## Summary",
            "",
            f"- cost_matrix_path: {summary['cost_matrix_path']}",
            f"- row_count: {summary['row_count']}",
            f"- venues: {summary['venues']}",
            f"- symbols: {summary['symbols']}",
            "",
            "## Rows",
            "",
        ]
    )
    if row_count:
        for row in frame.to_dicts():
            lines.append(
                f"- venue={row.get('venue')} symbol={row.get('symbol')} "
                f"spread_p50_bps={row.get('spread_p50_bps')} stale_rate={row.get('stale_rate')} "
                f"tradable_rate={row.get('tradable_rate')}"
            )
    else:
        lines.append("- rows: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
