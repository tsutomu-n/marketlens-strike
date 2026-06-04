from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sis.models import MarketStatus, QuoteLog, SessionType, Venue
from sis.venues.trade_xyz.quality import TradeXyzQualityPolicy, quality_blocks


@dataclass(frozen=True)
class BookMetrics:
    best_bid: float | None
    best_ask: float | None
    mid_price: float | None
    spread_bps: float | None
    depth_10bps_usd: float | None
    depth_25bps_usd: float | None
    bid_depth_10bps_usd: float | None
    ask_depth_10bps_usd: float | None
    bid_depth_25bps_usd: float | None
    ask_depth_25bps_usd: float | None
    block_reasons: list[str]


def _to_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _to_float_allow_zero(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _levels(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    levels = payload.get("levels")
    if not isinstance(levels, list) or len(levels) < 2:
        return [], []
    bids = levels[0] if isinstance(levels[0], list) else []
    asks = levels[1] if isinstance(levels[1], list) else []
    return [x for x in bids if isinstance(x, dict)], [x for x in asks if isinstance(x, dict)]


def compute_book_metrics(payload: dict[str, Any]) -> BookMetrics:
    bids, asks = _levels(payload)
    bid_prices = [_to_float(row.get("px")) for row in bids]
    ask_prices = [_to_float(row.get("px")) for row in asks]
    bid_prices = [x for x in bid_prices if x is not None]
    ask_prices = [x for x in ask_prices if x is not None]

    best_bid = max(bid_prices) if bid_prices else None
    best_ask = min(ask_prices) if ask_prices else None
    block_reasons: list[str] = []
    if best_bid is None:
        block_reasons.append("BLOCK_NO_BID")
    if best_ask is None:
        block_reasons.append("BLOCK_NO_ASK")
    if best_bid is None or best_ask is None:
        return BookMetrics(
            best_bid, best_ask, None, None, None, None, None, None, None, None, block_reasons
        )

    mid = (best_bid + best_ask) / 2
    spread_bps = (best_ask - best_bid) / mid * 10_000 if mid > 0 else None

    def depth_within(rows: list[dict[str, Any]], bps: float) -> float:
        total = 0.0
        low = mid * (1 - bps / 10_000)
        high = mid * (1 + bps / 10_000)
        for row in rows:
            px = _to_float(row.get("px"))
            sz = _to_float(row.get("sz"))
            if px is None or sz is None:
                continue
            if low <= px <= high:
                total += px * sz
        return total

    bid_depth_10 = depth_within(bids, 10)
    ask_depth_10 = depth_within(asks, 10)
    bid_depth_25 = depth_within(bids, 25)
    ask_depth_25 = depth_within(asks, 25)
    return BookMetrics(
        best_bid,
        best_ask,
        mid,
        spread_bps,
        bid_depth_10 + ask_depth_10,
        bid_depth_25 + ask_depth_25,
        bid_depth_10,
        ask_depth_10,
        bid_depth_25,
        ask_depth_25,
        block_reasons,
    )


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_ts_ms(payload: dict[str, Any]) -> int | None:
    for key in ("time", "ts", "timestamp"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _to_int_ms(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _oracle_ts_fields(
    asset_ctx: dict[str, Any] | None,
) -> tuple[int | None, str | None, str, str | None]:
    if not asset_ctx:
        return None, None, "missing", "asset_ctx_missing"
    for key in (
        "oracleTs",
        "oracle_ts",
        "oracleTsMs",
        "oracle_ts_ms",
        "oracleTime",
        "oracle_time",
        "oracleTimestamp",
        "oracle_timestamp",
    ):
        if key not in asset_ctx:
            continue
        parsed = _to_int_ms(asset_ctx.get(key))
        if parsed is None:
            return None, key, "invalid", f"invalid_oracle_ts_field:{key}"
        return parsed, key, "observed", None
    return None, None, "missing", "asset_ctx_missing_oracle_timestamp_field"


def _oracle_freshness_fields(
    *,
    oracle_price: float | None,
    source_ts_ms: int | None,
    recv_ts_ms: int | None,
) -> tuple[int | None, int | None, int | None, str, str]:
    if oracle_price is None:
        return (
            None,
            None,
            None,
            "missing_oracle_price",
            ("No oracle freshness proxy is recorded because oracle_price is missing."),
        )
    if source_ts_ms is None or recv_ts_ms is None:
        return (
            source_ts_ms,
            recv_ts_ms,
            None,
            "missing_snapshot_timestamp",
            (
                "oracle_freshness_* is a snapshot timing proxy; source_ts_ms and recv_ts_ms "
                "are both required."
            ),
        )
    lag_ms = recv_ts_ms - source_ts_ms
    if lag_ms < 0:
        return (
            source_ts_ms,
            recv_ts_ms,
            None,
            "invalid_clock_order",
            ("source_ts_ms is later than recv_ts_ms; do not treat this as oracle freshness."),
        )
    return (
        source_ts_ms,
        recv_ts_ms,
        lag_ms,
        "observed_snapshot_lag",
        (
            "This is not oracle_ts_ms. It measures raw snapshot receive lag for rows with "
            "oracle_price."
        ),
    )


def _datetime_from_ms(value: int | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _row_payload_data(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _row_payload_hash(row: dict[str, Any]) -> str:
    value = row.get("payload_sha256")
    if isinstance(value, str) and value:
        return value
    payload = row.get("payload")
    return payload_hash(payload if isinstance(payload, dict) else row)


def _row_symbol_fields(row: dict[str, Any], data: dict[str, Any]) -> tuple[str, str, str]:
    coin = row.get("coin") or data.get("coin")
    canonical_symbol = row.get("canonical_symbol")
    venue_symbol = row.get("venue_symbol") or coin or canonical_symbol
    if not isinstance(canonical_symbol, str) or not canonical_symbol:
        canonical_symbol = str(coin).split(":", 1)[-1] if coin else "UNKNOWN"
    if not isinstance(venue_symbol, str) or not venue_symbol:
        venue_symbol = canonical_symbol
    if not isinstance(coin, str) or not coin:
        coin = venue_symbol
    return canonical_symbol, venue_symbol, coin


def _bbo_metrics(data: dict[str, Any]) -> BookMetrics:
    bbo = data.get("bbo")
    if not isinstance(bbo, list) or len(bbo) < 2:
        return BookMetrics(None, None, None, None, None, None, None, None, None, None, [])
    bid = bbo[0] if isinstance(bbo[0], dict) else {}
    ask = bbo[1] if isinstance(bbo[1], dict) else {}
    best_bid = _to_float(bid.get("px"))
    best_ask = _to_float(ask.get("px"))
    bid_size = _to_float(bid.get("sz"))
    ask_size = _to_float(ask.get("sz"))
    block_reasons: list[str] = []
    if best_bid is None:
        block_reasons.append("BLOCK_NO_BID")
    if best_ask is None:
        block_reasons.append("BLOCK_NO_ASK")
    if best_bid is None or best_ask is None:
        return BookMetrics(
            best_bid, best_ask, None, None, None, None, None, None, None, None, block_reasons
        )
    mid = (best_bid + best_ask) / 2
    spread_bps = (best_ask - best_bid) / mid * 10_000 if mid > 0 else None
    bid_depth = best_bid * bid_size if bid_size is not None else None
    ask_depth = best_ask * ask_size if ask_size is not None else None
    total_depth = bid_depth + ask_depth if bid_depth is not None and ask_depth is not None else None
    return BookMetrics(
        best_bid,
        best_ask,
        mid,
        spread_bps,
        total_depth,
        total_depth,
        bid_depth,
        ask_depth,
        bid_depth,
        ask_depth,
        block_reasons,
    )


def quote_from_ws_bbo_row(
    row: dict[str, Any],
    *,
    asset_id: int | None = None,
    real_market_symbol: str | None = None,
    fee_mode: str | None = None,
    taker_fee_bps: float | None = None,
    maker_fee_bps: float | None = None,
    quality_policy: TradeXyzQualityPolicy | None = None,
) -> QuoteLog:
    data = _row_payload_data(row)
    canonical_symbol, venue_symbol, coin = _row_symbol_fields(row, data)
    recv_ts_ms = _to_int_ms(row.get("recv_ts_ms"))
    source_ts_ms = _to_int_ms(row.get("source_ts_ms")) or _source_ts_ms(data)
    metrics = _bbo_metrics(data)
    quality_reasons = quality_blocks(
        spread_bps=metrics.spread_bps,
        depth_10bps_usd=metrics.depth_10bps_usd,
        recv_ts_ms=recv_ts_ms,
        source_ts_ms=source_ts_ms,
        policy=quality_policy,
    )
    block_reasons = list(dict.fromkeys(metrics.block_reasons + quality_reasons))
    oracle_ts_ms, oracle_ts_source, oracle_ts_status, oracle_ts_missing_reason = _oracle_ts_fields(
        None
    )
    (
        oracle_freshness_source_ts_ms,
        oracle_freshness_recv_ts_ms,
        oracle_freshness_lag_ms,
        oracle_freshness_status,
        oracle_freshness_note,
    ) = _oracle_freshness_fields(
        oracle_price=None,
        source_ts_ms=source_ts_ms,
        recv_ts_ms=recv_ts_ms,
    )
    return QuoteLog(
        ts_client=_datetime_from_ms(recv_ts_ms),
        venue=Venue.TRADE_XYZ,
        canonical_symbol=canonical_symbol,
        venue_symbol=venue_symbol,
        dex="xyz",
        coin=coin,
        asset_id=asset_id,
        real_market_symbol=real_market_symbol,
        recv_ts_ms=recv_ts_ms,
        source_ts_ms=source_ts_ms,
        best_bid=metrics.best_bid,
        best_ask=metrics.best_ask,
        bid_price=metrics.best_bid,
        ask_price=metrics.best_ask,
        mid_price=metrics.mid_price,
        exec_buy_price=metrics.best_ask,
        exec_sell_price=metrics.best_bid,
        spread_bps=metrics.spread_bps,
        depth_10bps_usd=metrics.depth_10bps_usd,
        depth_25bps_usd=metrics.depth_25bps_usd,
        bid_depth_10bps_usd=metrics.bid_depth_10bps_usd,
        ask_depth_10bps_usd=metrics.ask_depth_10bps_usd,
        bid_depth_25bps_usd=metrics.bid_depth_25bps_usd,
        ask_depth_25bps_usd=metrics.ask_depth_25bps_usd,
        min_side_depth_10bps_usd=(
            min(metrics.bid_depth_10bps_usd, metrics.ask_depth_10bps_usd)
            if metrics.bid_depth_10bps_usd is not None and metrics.ask_depth_10bps_usd is not None
            else None
        ),
        fee_mode=fee_mode or "unknown",
        taker_fee_bps=taker_fee_bps,
        maker_fee_bps=maker_fee_bps,
        fee_source="instrument_registry"
        if taker_fee_bps is not None and maker_fee_bps is not None
        else "unresolved",
        oracle_ts_ms=oracle_ts_ms,
        oracle_ts_source=oracle_ts_source,
        oracle_ts_status=oracle_ts_status,
        oracle_ts_missing_reason=oracle_ts_missing_reason,
        oracle_freshness_source_ts_ms=oracle_freshness_source_ts_ms,
        oracle_freshness_recv_ts_ms=oracle_freshness_recv_ts_ms,
        oracle_freshness_lag_ms=oracle_freshness_lag_ms,
        oracle_freshness_status=oracle_freshness_status,
        oracle_freshness_note=oracle_freshness_note,
        market_status=MarketStatus.OPEN if not block_reasons else MarketStatus.UNKNOWN,
        session_type=SessionType.UNKNOWN,
        is_tradable=not block_reasons,
        source_confidence=1.0,
        venue_quality_score=1.0 if not block_reasons else 0.5,
        block_reasons=block_reasons,
        source="trade_xyz_ws_bbo",
        raw_payload_sha256=_row_payload_hash(row),
        raw_payload_ref=row.get("raw_payload_ref")
        if isinstance(row.get("raw_payload_ref"), str)
        else None,
        raw_payload=row,
    )


def quote_from_ws_active_asset_ctx_row(
    row: dict[str, Any],
    *,
    asset_id: int | None = None,
    real_market_symbol: str | None = None,
) -> QuoteLog:
    data = _row_payload_data(row)
    ctx = data.get("ctx")
    ctx = ctx if isinstance(ctx, dict) else {}
    canonical_symbol, venue_symbol, coin = _row_symbol_fields(row, data)
    recv_ts_ms = _to_int_ms(row.get("recv_ts_ms"))
    source_ts_ms = _to_int_ms(row.get("source_ts_ms"))
    mark_price = _to_float(ctx.get("markPx") or ctx.get("mark_price"))
    oracle_price = _to_float(ctx.get("oraclePx") or ctx.get("oracle_price"))
    mid_price = _to_float(ctx.get("midPx") or ctx.get("mid_price"))
    index_price = _to_float(ctx.get("indexPx") or ctx.get("index_price") or ctx.get("midPx"))
    funding_rate = _to_float_allow_zero(ctx.get("funding") or ctx.get("funding_rate"))
    open_interest_usd = _to_float(ctx.get("openInterest") or ctx.get("open_interest_usd"))
    oi_cap_usd = _to_float(ctx.get("openInterestCap") or ctx.get("oi_cap_usd"))
    premium = _to_float(ctx.get("premium"))
    prev_day_price = _to_float(ctx.get("prevDayPx") or ctx.get("prev_day_price"))
    day_notional_volume = _to_float(ctx.get("dayNtlVlm") or ctx.get("day_notional_volume"))
    oracle_ts_ms, oracle_ts_source, oracle_ts_status, oracle_ts_missing_reason = _oracle_ts_fields(
        ctx
    )
    (
        oracle_freshness_source_ts_ms,
        oracle_freshness_recv_ts_ms,
        oracle_freshness_lag_ms,
        oracle_freshness_status,
        oracle_freshness_note,
    ) = _oracle_freshness_fields(
        oracle_price=oracle_price,
        source_ts_ms=source_ts_ms,
        recv_ts_ms=recv_ts_ms,
    )
    return QuoteLog(
        ts_client=_datetime_from_ms(recv_ts_ms),
        venue=Venue.TRADE_XYZ,
        canonical_symbol=canonical_symbol,
        venue_symbol=venue_symbol,
        dex="xyz",
        coin=coin,
        asset_id=asset_id,
        real_market_symbol=real_market_symbol,
        recv_ts_ms=recv_ts_ms,
        source_ts_ms=source_ts_ms,
        mark_price=mark_price,
        oracle_price=oracle_price,
        index_price=index_price,
        mid_price=mid_price,
        funding_rate=funding_rate,
        funding_interval_minutes=60 if funding_rate is not None else None,
        open_interest_usd=open_interest_usd,
        oi_cap_usd=oi_cap_usd,
        oi_cap_usage=(
            open_interest_usd / oi_cap_usd
            if open_interest_usd is not None and oi_cap_usd is not None and oi_cap_usd > 0
            else None
        ),
        premium=premium,
        prev_day_price=prev_day_price,
        day_notional_volume=day_notional_volume,
        fee_mode="unknown",
        fee_source="unresolved",
        oracle_ts_ms=oracle_ts_ms,
        oracle_ts_source=oracle_ts_source,
        oracle_ts_status=oracle_ts_status,
        oracle_ts_missing_reason=oracle_ts_missing_reason,
        oracle_freshness_source_ts_ms=oracle_freshness_source_ts_ms,
        oracle_freshness_recv_ts_ms=oracle_freshness_recv_ts_ms,
        oracle_freshness_lag_ms=oracle_freshness_lag_ms,
        oracle_freshness_status=oracle_freshness_status,
        oracle_freshness_note=oracle_freshness_note,
        market_status=MarketStatus.UNKNOWN,
        session_type=SessionType.UNKNOWN,
        is_tradable=False,
        source_confidence=1.0,
        venue_quality_score=0.5,
        block_reasons=["BLOCK_NO_BBO_FILL_SNAPSHOT"],
        source="trade_xyz_ws_activeAssetCtx",
        raw_payload_sha256=_row_payload_hash(row),
        raw_payload_ref=row.get("raw_payload_ref")
        if isinstance(row.get("raw_payload_ref"), str)
        else None,
        raw_payload=row,
    )


def quote_from_l2_book(
    *,
    canonical_symbol: str,
    coin: str,
    asset_id: int | None,
    real_market_symbol: str | None,
    payload: dict[str, Any],
    asset_ctx: dict[str, Any] | None = None,
    fee_mode: str | None = None,
    taker_fee_bps: float | None = None,
    maker_fee_bps: float | None = None,
    source: str = "trade_xyz_l2Book",
    now: datetime | None = None,
    quality_policy: TradeXyzQualityPolicy | None = None,
) -> QuoteLog:
    ts = now or datetime.now(timezone.utc)
    recv_ts_ms = int(ts.timestamp() * 1000)
    source_ts_ms = _source_ts_ms(payload)
    metrics = compute_book_metrics(payload)
    quality_reasons = quality_blocks(
        spread_bps=metrics.spread_bps,
        depth_10bps_usd=metrics.depth_10bps_usd,
        recv_ts_ms=recv_ts_ms,
        source_ts_ms=source_ts_ms,
        policy=quality_policy,
    )
    block_reasons = list(dict.fromkeys(metrics.block_reasons + quality_reasons))
    ctx = asset_ctx or {}
    oracle_ts_ms, oracle_ts_source, oracle_ts_status, oracle_ts_missing_reason = _oracle_ts_fields(
        asset_ctx
    )
    mark_price = _to_float(ctx.get("markPx") or ctx.get("mark_price"))
    oracle_price = _to_float(ctx.get("oraclePx") or ctx.get("oracle_price"))
    index_price = _to_float(ctx.get("indexPx") or ctx.get("index_price") or ctx.get("midPx"))
    funding_rate = _to_float_allow_zero(ctx.get("funding") or ctx.get("funding_rate"))
    open_interest_usd = _to_float(ctx.get("openInterest") or ctx.get("open_interest_usd"))
    oi_cap_usd = _to_float(ctx.get("openInterestCap") or ctx.get("oi_cap_usd"))
    premium = _to_float(ctx.get("premium"))
    prev_day_price = _to_float(ctx.get("prevDayPx") or ctx.get("prev_day_price"))
    day_notional_volume = _to_float(ctx.get("dayNtlVlm") or ctx.get("day_notional_volume"))
    last_trade_price = _to_float(ctx.get("lastPx") or ctx.get("last_price") or ctx.get("last"))
    if ctx and mark_price is None:
        block_reasons.append("BLOCK_MARK_PRICE_MISSING")
    if ctx and oracle_price is None:
        block_reasons.append("BLOCK_ORACLE_PRICE_MISSING")
    if ctx and funding_rate is None:
        block_reasons.append("BLOCK_FUNDING_MISSING")
    if ctx and open_interest_usd is None:
        block_reasons.append("BLOCK_OPEN_INTEREST_MISSING")
    (
        oracle_freshness_source_ts_ms,
        oracle_freshness_recv_ts_ms,
        oracle_freshness_lag_ms,
        oracle_freshness_status,
        oracle_freshness_note,
    ) = _oracle_freshness_fields(
        oracle_price=oracle_price,
        source_ts_ms=source_ts_ms,
        recv_ts_ms=recv_ts_ms,
    )
    return QuoteLog(
        ts_client=ts,
        venue=Venue.TRADE_XYZ,
        canonical_symbol=canonical_symbol,
        venue_symbol=canonical_symbol,
        dex="xyz",
        coin=coin,
        asset_id=asset_id,
        real_market_symbol=real_market_symbol,
        recv_ts_ms=recv_ts_ms,
        source_ts_ms=source_ts_ms,
        best_bid=metrics.best_bid,
        best_ask=metrics.best_ask,
        bid_price=metrics.best_bid,
        ask_price=metrics.best_ask,
        mid_price=metrics.mid_price,
        last_trade_price=last_trade_price,
        exec_buy_price=metrics.best_ask,
        exec_sell_price=metrics.best_bid,
        spread_bps=metrics.spread_bps,
        depth_10bps_usd=metrics.depth_10bps_usd,
        depth_25bps_usd=metrics.depth_25bps_usd,
        bid_depth_10bps_usd=metrics.bid_depth_10bps_usd,
        ask_depth_10bps_usd=metrics.ask_depth_10bps_usd,
        bid_depth_25bps_usd=metrics.bid_depth_25bps_usd,
        ask_depth_25bps_usd=metrics.ask_depth_25bps_usd,
        min_side_depth_10bps_usd=(
            min(metrics.bid_depth_10bps_usd, metrics.ask_depth_10bps_usd)
            if metrics.bid_depth_10bps_usd is not None and metrics.ask_depth_10bps_usd is not None
            else None
        ),
        mark_price=mark_price,
        oracle_price=oracle_price,
        index_price=index_price,
        funding_rate=funding_rate,
        funding_interval_minutes=60 if funding_rate is not None else None,
        open_interest_usd=open_interest_usd,
        oi_cap_usd=oi_cap_usd,
        oi_cap_usage=(
            open_interest_usd / oi_cap_usd
            if open_interest_usd is not None and oi_cap_usd is not None and oi_cap_usd > 0
            else None
        ),
        premium=premium,
        prev_day_price=prev_day_price,
        day_notional_volume=day_notional_volume,
        fee_mode=fee_mode or "unknown",
        taker_fee_bps=taker_fee_bps,
        maker_fee_bps=maker_fee_bps,
        fee_source="instrument_registry"
        if taker_fee_bps is not None and maker_fee_bps is not None
        else "unresolved",
        oracle_ts_ms=oracle_ts_ms,
        oracle_ts_source=oracle_ts_source,
        oracle_ts_status=oracle_ts_status,
        oracle_ts_missing_reason=oracle_ts_missing_reason,
        oracle_freshness_source_ts_ms=oracle_freshness_source_ts_ms,
        oracle_freshness_recv_ts_ms=oracle_freshness_recv_ts_ms,
        oracle_freshness_lag_ms=oracle_freshness_lag_ms,
        oracle_freshness_status=oracle_freshness_status,
        oracle_freshness_note=oracle_freshness_note,
        market_status=MarketStatus.OPEN if not block_reasons else MarketStatus.UNKNOWN,
        session_type=SessionType.UNKNOWN,
        is_tradable=not block_reasons,
        source_confidence=1.0,
        venue_quality_score=1.0 if not block_reasons else 0.5,
        block_reasons=block_reasons,
        source=source,
        raw_payload_sha256=payload_hash(payload),
        raw_payload=payload,
    )
