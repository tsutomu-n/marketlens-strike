from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Literal

import polars as pl

from sis.backtest.trade_xyz.market_data import (
    CloseSource,
    EventTimeSource,
    prepare_quote_rows_for_backtest,
)


Timeframe = Literal["30m", "1h", "4h", "1d"]

_TIMEFRAME_SECONDS: dict[Timeframe, int] = {
    "30m": 30 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}


def _as_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"event_ts must be datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _bar_close(value: datetime, *, seconds: int) -> datetime:
    epoch = int(value.timestamp())
    close_epoch = ((epoch // seconds) + 1) * seconds
    return datetime.fromtimestamp(close_epoch, tz=timezone.utc)


def _first_non_null(row: dict[str, Any], *fields: str) -> float | None:
    for field in fields:
        value = row.get(field)
        if isinstance(value, int | float) and float(value) > 0:
            return float(value)
    return None


def _exec_buy(row: dict[str, Any]) -> float | None:
    return _first_non_null(row, "exec_buy_price")


def _exec_sell(row: dict[str, Any]) -> float | None:
    return _first_non_null(row, "exec_sell_price")


def _buy_fill_candidate(row: dict[str, Any]) -> float | None:
    direct = _first_non_null(row, "exec_buy_price", "best_ask", "ask_price")
    if direct is not None:
        return direct
    mid = _first_non_null(row, "mid_price")
    spread = row.get("spread_bps")
    if mid is not None and isinstance(spread, int | float):
        return mid * (1 + float(spread) / 20_000)
    return None


def _sell_fill_candidate(row: dict[str, Any]) -> float | None:
    direct = _first_non_null(row, "exec_sell_price", "best_bid", "bid_price")
    if direct is not None:
        return direct
    mid = _first_non_null(row, "mid_price")
    spread = row.get("spread_bps")
    if mid is not None and isinstance(spread, int | float):
        return mid * (1 - float(spread) / 20_000)
    return None


def _block_reasons(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]


def _last_non_null(rows: list[dict[str, Any]], field: str) -> Any:
    for row in reversed(rows):
        value = row.get(field)
        if value is not None:
            return value
    return None


def _first_executable(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if _buy_fill_candidate(row) is not None or _sell_fill_candidate(row) is not None:
            return row
    return rows[0]


def build_quote_bars(
    frame: pl.DataFrame,
    *,
    symbol: str,
    timeframe: Timeframe = "1h",
    close_source: CloseSource = "mid_price",
    event_time_source: EventTimeSource = "ts_client",
) -> pl.DataFrame:
    """Build bar-like rows from prepared or normalized Trade[XYZ] quote rows."""
    if timeframe not in _TIMEFRAME_SECONDS:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    prepared = (
        frame
        if {"event_ts", "symbol", "close"}.issubset(frame.columns)
        else prepare_quote_rows_for_backtest(
            frame,
            symbol=symbol,
            close_source=close_source,
            event_time_source=event_time_source,
        )
    )
    if close_source not in prepared.columns and "close" not in prepared.columns:
        raise ValueError(f"missing close_source column: {close_source}")

    rows = prepared.sort("event_ts").to_dicts()
    grouped: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    seconds = _TIMEFRAME_SECONDS[timeframe]
    for row in rows:
        grouped[_bar_close(_as_datetime(row["event_ts"]), seconds=seconds)].append(row)

    bars: list[dict[str, Any]] = []
    for event_ts in sorted(grouped):
        group = grouped[event_ts]
        signal_row = group[-1]
        fill_row = _first_executable(group)
        closes = [float(row["close"]) for row in group if isinstance(row.get("close"), int | float)]
        if not closes:
            continue
        union: list[str] = []
        for row in group:
            for reason in _block_reasons(row.get("block_reasons")):
                if reason not in union:
                    union.append(reason)
        fill_block_reasons = _block_reasons(fill_row.get("block_reasons"))
        bars.append(
            {
                "event_ts": event_ts,
                "symbol": symbol.strip().upper(),
                "open": closes[0],
                "high": max(closes),
                "low": min(closes),
                "close": closes[-1],
                "signal_is_tradable": signal_row.get("is_tradable"),
                "signal_market_status": signal_row.get("market_status"),
                "signal_block_reasons": _block_reasons(signal_row.get("block_reasons")),
                "session_type": _last_non_null(group, "session_type"),
                "fill_is_tradable": fill_row.get("is_tradable"),
                "fill_market_status": fill_row.get("market_status"),
                "fill_block_reasons": fill_block_reasons,
                "fill_best_bid": fill_row.get("best_bid"),
                "fill_best_ask": fill_row.get("best_ask"),
                "fill_mid_price": fill_row.get("mid_price"),
                "fill_spread_bps": fill_row.get("spread_bps"),
                "fill_min_side_depth_10bps_usd": fill_row.get("min_side_depth_10bps_usd"),
                "fill_bound_distance": fill_row.get("bound_distance"),
                "fill_oi_cap_usage": fill_row.get("oi_cap_usage"),
                "fill_taker_fee_bps": fill_row.get("taker_fee_bps"),
                "fill_maker_fee_bps": fill_row.get("maker_fee_bps"),
                "fill_fee_mode": fill_row.get("fee_mode"),
                "exec_buy_price": _exec_buy(fill_row),
                "exec_sell_price": _exec_sell(fill_row),
                "best_bid": fill_row.get("best_bid"),
                "best_ask": fill_row.get("best_ask"),
                "mid_price": fill_row.get("mid_price"),
                "spread_bps": fill_row.get("spread_bps"),
                "is_tradable": signal_row.get("is_tradable"),
                "market_status": signal_row.get("market_status"),
                "block_reasons": _block_reasons(signal_row.get("block_reasons")),
                "taker_fee_bps": fill_row.get("taker_fee_bps"),
                "maker_fee_bps": fill_row.get("maker_fee_bps"),
                "fee_mode": fill_row.get("fee_mode"),
                "min_side_depth_10bps_usd": fill_row.get("min_side_depth_10bps_usd"),
                "bound_distance": fill_row.get("bound_distance"),
                "oi_cap_usage": fill_row.get("oi_cap_usage"),
                "funding_rate": _last_non_null(group, "funding_rate"),
                "is_funding_event": False,
                "bar_max_spread_bps": max(
                    [
                        float(row["spread_bps"])
                        for row in group
                        if isinstance(row.get("spread_bps"), int | float)
                    ],
                    default=None,
                ),
                "bar_min_side_depth_10bps_usd": min(
                    [
                        float(row["min_side_depth_10bps_usd"])
                        for row in group
                        if isinstance(row.get("min_side_depth_10bps_usd"), int | float)
                    ],
                    default=None,
                ),
                "bar_block_reason_union": union,
                "timeframe": timeframe,
                "bar_builder": "quote_bar_v1",
                "close_source": close_source,
                "event_time_source": _last_non_null(group, "event_time_source") or "event_ts",
            }
        )
    if not bars:
        return pl.DataFrame()
    return pl.from_dicts(bars).sort("event_ts")
