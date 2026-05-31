from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import polars as pl


CloseSource = Literal["mid_price", "mark_price", "oracle_price", "index_price"]
EventTimeSource = Literal["ts_client", "source_ts_ms", "recv_ts_ms"]


def load_normalized_quotes(path: Path) -> pl.DataFrame:
    """Read normalized Trade[XYZ] quote parquet."""
    return pl.read_parquet(path)


def _symbol_column(frame: pl.DataFrame) -> str:
    if "canonical_symbol" in frame.columns:
        return "canonical_symbol"
    if "symbol" in frame.columns:
        return "symbol"
    raise ValueError("missing symbol column: canonical_symbol or symbol")


def _event_ts_expr(source: EventTimeSource) -> pl.Expr:
    if source == "ts_client":
        return pl.col("ts_client").str.to_datetime(time_zone="UTC", strict=False)
    return pl.from_epoch(pl.col(source), time_unit="ms").dt.replace_time_zone("UTC")


def prepare_quote_rows_for_backtest(
    frame: pl.DataFrame,
    *,
    symbol: str,
    close_source: CloseSource = "mid_price",
    event_time_source: EventTimeSource = "ts_client",
) -> pl.DataFrame:
    """
    Convert normalized Trade[XYZ] quote rows into run_backtest-compatible rows.
    """
    if frame.is_empty():
        raise ValueError("normalized quote frame is empty")
    if close_source not in frame.columns:
        raise ValueError(f"missing close_source column: {close_source}")
    if event_time_source not in frame.columns:
        raise ValueError(f"missing event_time_source column: {event_time_source}")

    target_symbol = symbol.strip().upper()
    symbol_column = _symbol_column(frame)
    filtered = frame.with_columns(
        pl.col(symbol_column).cast(pl.Utf8).str.strip_chars().str.to_uppercase().alias("_symbol")
    ).filter(pl.col("_symbol") == target_symbol)
    if filtered.is_empty():
        raise ValueError(f"no rows for symbol: {target_symbol}")
    if filtered.select(pl.col(close_source).is_not_null().sum()).item() == 0:
        raise ValueError(f"close_source column is all null: {close_source}")

    prepared = filtered.with_columns(
        [
            _event_ts_expr(event_time_source).alias("event_ts"),
            pl.col("_symbol").alias("symbol"),
            pl.col(close_source).cast(pl.Float64).alias("close"),
            pl.lit(event_time_source).alias("event_time_source"),
            pl.lit(close_source).alias("close_source"),
        ]
    )
    if "index_price" in prepared.columns and "external_price" not in prepared.columns:
        prepared = prepared.with_columns(pl.col("index_price").alias("external_price"))
    if "min_side_depth_10bps_usd" not in prepared.columns:
        if {"bid_depth_10bps_usd", "ask_depth_10bps_usd"}.issubset(prepared.columns):
            prepared = prepared.with_columns(
                pl.min_horizontal("bid_depth_10bps_usd", "ask_depth_10bps_usd").alias(
                    "min_side_depth_10bps_usd"
                )
            )
        elif "depth_10bps_usd" in prepared.columns:
            prepared = prepared.with_columns(
                pl.col("depth_10bps_usd").alias("min_side_depth_10bps_usd")
            )
        else:
            prepared = prepared.with_columns(
                pl.lit(None, dtype=pl.Float64).alias("min_side_depth_10bps_usd")
            )

    return prepared.drop("_symbol").sort("event_ts")


def infer_period_from_event_ts(frame: pl.DataFrame) -> tuple[datetime, datetime]:
    """Return min/max event_ts bounds."""
    if frame.is_empty() or "event_ts" not in frame.columns:
        raise ValueError("event_ts column is required")
    first = frame.get_column("event_ts").min()
    last = frame.get_column("event_ts").max()
    if not isinstance(first, datetime) or not isinstance(last, datetime):
        raise ValueError("event_ts bounds must be datetime values")
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return first, last
