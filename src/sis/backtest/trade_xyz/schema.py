from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl


REQUIRED_CANONICAL_COLUMNS = {
    "event_ts",
    "symbol",
    "is_tradable",
    "block_reasons",
}

RESERVED_COLUMNS: dict[str, Any] = {
    "source_ts_ms": pl.Int64,
    "recv_ts_ms": pl.Int64,
    "oracle_ts_ms": pl.Int64,
    "mark_price": pl.Float64,
    "oracle_price": pl.Float64,
    "external_price": pl.Float64,
    "funding_rate": pl.Float64,
    "funding_interval_minutes": pl.Int64,
    "open_interest_usd": pl.Float64,
    "last_trade_price": pl.Float64,
    "oi_cap_usd": pl.Float64,
    "oi_cap_usage": pl.Float64,
    "discovery_bound_pct": pl.Float64,
    "bound_distance": pl.Float64,
    "session_type": pl.Utf8,
    "market_status": pl.Utf8,
    "source_confidence": pl.Float64,
    "venue_quality_score": pl.Float64,
    "depth_10bps_usd": pl.Float64,
    "min_side_depth_10bps_usd": pl.Float64,
    "taker_fee_bps": pl.Float64,
    "maker_fee_bps": pl.Float64,
    "fee_mode": pl.Utf8,
    "fee_source": pl.Utf8,
    "best_bid": pl.Float64,
    "best_ask": pl.Float64,
    "bid_price": pl.Float64,
    "ask_price": pl.Float64,
    "mid_price": pl.Float64,
    "close": pl.Float64,
    "spread_bps": pl.Float64,
    "exec_buy_price": pl.Float64,
    "exec_sell_price": pl.Float64,
    "raw_payload_ref": pl.Utf8,
}


def _column_expr(frame: pl.DataFrame, *names: str) -> pl.Expr:
    for name in names:
        if name in frame.columns:
            return pl.col(name)
    return pl.lit(None)


def _parse_event_ts(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError(f"unsupported event_ts value: {value!r}")
    if parsed.tzinfo is None:
        raise ValueError("event_ts must be timezone-aware")
    return parsed


def _block_reasons(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, pl.Series):
        return [str(item) for item in value.to_list() if item is not None and str(item)]
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None and str(item)]
    if isinstance(value, str):
        return [value] if value else []
    raise ValueError(f"block_reasons must be list[str], got {type(value).__name__}")


def normalize_trade_xyz_market_data(frame: pl.DataFrame, *, symbol: str) -> pl.DataFrame:
    if frame.is_empty():
        raise ValueError("market data frame is empty")

    target_symbol = symbol.strip().upper()
    normalized = frame.with_columns(
        [
            _column_expr(frame, "event_ts", "ts_client").alias("event_ts"),
            _column_expr(frame, "symbol", "canonical_symbol").alias("symbol"),
            _column_expr(frame, "index_price", "external_price").alias("external_price"),
            _column_expr(frame, "best_bid", "bid_price").alias("best_bid"),
            _column_expr(frame, "best_ask", "ask_price").alias("best_ask"),
        ]
    )
    normalized = normalized.with_columns(
        [
            pl.col("event_ts").map_elements(_parse_event_ts, return_dtype=pl.Datetime("us", "UTC")),
            pl.col("symbol").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
            pl.col("block_reasons")
            .map_elements(_block_reasons, return_dtype=pl.List(pl.Utf8))
            .alias("block_reasons"),
        ]
    )

    for column, dtype in RESERVED_COLUMNS.items():
        if column not in normalized.columns:
            normalized = normalized.with_columns(pl.lit(None, dtype=dtype).alias(column))
    if "block_reasons" not in normalized.columns:
        raise ValueError("missing required columns: block_reasons")
    if "is_tradable" not in normalized.columns:
        raise ValueError("missing required columns: is_tradable")
    normalized = normalized.with_columns(pl.col("is_tradable").cast(pl.Boolean))

    symbols = set(normalized.get_column("symbol").drop_nulls().to_list())
    if symbols != {target_symbol}:
        raise ValueError(f"symbol mismatch: expected {target_symbol}, got {sorted(symbols)}")

    price_candidates = [
        column
        for column in ("mid_price", "close", "best_bid", "best_ask", "external_price")
        if column in normalized.columns
    ]
    if price_candidates:
        invalid = normalized.select(
            pl.any_horizontal(
                [
                    pl.col(column).is_not_null() & (pl.col(column) <= 0)
                    for column in price_candidates
                ]
            ).sum()
        ).item()
        if invalid:
            raise ValueError("price columns must be positive when present")

    return normalized.sort(["symbol", "event_ts"])
