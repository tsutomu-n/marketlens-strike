from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import polars as pl

from sis.backtest.trade_xyz.bar_builder import Timeframe, build_quote_bars


STATE_COLUMNS: dict[str, Any] = {
    "state_observed_ts_ms": pl.Int64,
    "state_source": pl.Utf8,
    "state_mark_price": pl.Float64,
    "state_oracle_price": pl.Float64,
    "state_index_price": pl.Float64,
    "state_funding_rate": pl.Float64,
    "state_open_interest_usd": pl.Float64,
}

STATE_SOURCE_COLUMNS: dict[str, Any] = {
    "recv_ts_ms": pl.Int64,
    "mark_price": pl.Float64,
    "oracle_price": pl.Float64,
    "index_price": pl.Float64,
    "funding_rate": pl.Float64,
    "open_interest_usd": pl.Float64,
}


def _event_ts_ms(value: object) -> int:
    if not isinstance(value, datetime):
        raise ValueError(f"event_ts must be datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _empty_state_columns(frame: pl.DataFrame) -> pl.DataFrame:
    for name, dtype in STATE_COLUMNS.items():
        if name not in frame.columns:
            frame = frame.with_columns(pl.lit(None, dtype=dtype).alias(name))
    return frame


def _ensure_state_source_columns(frame: pl.DataFrame) -> pl.DataFrame:
    for name, dtype in STATE_SOURCE_COLUMNS.items():
        if name not in frame.columns:
            frame = frame.with_columns(pl.lit(None, dtype=dtype).alias(name))
    return frame


def _reject_missing_bbo_source_ts_ms(frame: pl.DataFrame) -> None:
    if "source_ts_ms" not in frame.columns:
        raise ValueError("WS BBO rows missing source_ts_ms")
    if frame.select(pl.col("source_ts_ms").is_null().sum()).item():
        raise ValueError("WS BBO rows missing source_ts_ms")


def _normalized_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must not be empty")
    return normalized


def _symbol_filter(
    frame: pl.DataFrame, symbol: str, *, row_name: str = "WS activeAssetCtx state"
) -> pl.Expr:
    if "canonical_symbol" in frame.columns:
        symbol_column = "canonical_symbol"
    elif "symbol" in frame.columns:
        symbol_column = "symbol"
    else:
        raise ValueError(f"{row_name} missing symbol column")
    return pl.col(symbol_column).cast(pl.Utf8).str.strip_chars().str.to_uppercase() == symbol


def build_bbo_bars_with_active_asset_state(
    frame: pl.DataFrame,
    *,
    symbol: str,
    timeframe: Timeframe = "1h",
) -> pl.DataFrame:
    """Build BBO fill bars and asof-join observed activeAssetCtx state without lookahead."""
    symbol = _normalized_symbol(symbol)
    if frame.is_empty():
        raise ValueError("WS quote frame is empty")
    if "source" not in frame.columns:
        raise ValueError("WS quote frame missing source column")

    bbo = frame.filter(pl.col("source") == "trade_xyz_ws_bbo")
    if bbo.is_empty():
        raise ValueError("WS quote frame has no bbo rows for fill snapshots")
    bbo = bbo.filter(_symbol_filter(bbo, symbol, row_name="WS BBO rows"))
    if bbo.is_empty():
        raise ValueError(f"WS quote frame has no bbo rows for symbol: {symbol}")
    _reject_missing_bbo_source_ts_ms(bbo)
    bars = build_quote_bars(
        bbo,
        symbol=symbol,
        timeframe=timeframe,
        close_source="mid_price",
        event_time_source="source_ts_ms",
    )
    if bars.is_empty():
        return _empty_state_columns(bars)

    state = frame.filter(pl.col("source") == "trade_xyz_ws_activeAssetCtx")
    if state.is_empty():
        return _empty_state_columns(bars)
    state = state.filter(_symbol_filter(state, symbol))
    if state.is_empty():
        return _empty_state_columns(bars)
    state = _ensure_state_source_columns(state)

    state_rows = (
        state.filter(pl.col("recv_ts_ms").is_not_null())
        .sort("recv_ts_ms")
        .select(
            [
                "recv_ts_ms",
                "source",
                "mark_price",
                "oracle_price",
                "index_price",
                "funding_rate",
                "open_interest_usd",
            ]
        )
        .to_dicts()
    )
    if not state_rows:
        return _empty_state_columns(bars)

    joined: list[dict[str, Any]] = []
    state_index = 0
    latest: dict[str, Any] | None = None
    for bar in bars.sort("event_ts").to_dicts():
        bar_ts_ms = _event_ts_ms(bar["event_ts"])
        while state_index < len(state_rows):
            candidate = state_rows[state_index]
            recv_ts_ms = candidate.get("recv_ts_ms")
            if not isinstance(recv_ts_ms, int | float) or int(recv_ts_ms) > bar_ts_ms:
                break
            latest = candidate
            state_index += 1
        if latest is None:
            joined.append(
                {
                    **bar,
                    "state_observed_ts_ms": None,
                    "state_source": None,
                    "state_mark_price": None,
                    "state_oracle_price": None,
                    "state_index_price": None,
                    "state_funding_rate": None,
                    "state_open_interest_usd": None,
                }
            )
            continue
        joined.append(
            {
                **bar,
                "state_observed_ts_ms": int(latest["recv_ts_ms"]),
                "state_source": latest["source"],
                "state_mark_price": latest["mark_price"],
                "state_oracle_price": latest["oracle_price"],
                "state_index_price": latest["index_price"],
                "state_funding_rate": latest["funding_rate"],
                "state_open_interest_usd": latest["open_interest_usd"],
            }
        )
    return pl.from_dicts(joined).sort("event_ts")
