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


def quote_from_l2_book(
    *,
    canonical_symbol: str,
    coin: str,
    asset_id: int | None,
    real_market_symbol: str | None,
    payload: dict[str, Any],
    asset_ctx: dict[str, Any] | None = None,
    fee_mode: str | None = None,
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
    mark_price = _to_float(ctx.get("markPx") or ctx.get("mark_price"))
    oracle_price = _to_float(ctx.get("oraclePx") or ctx.get("oracle_price"))
    index_price = _to_float(ctx.get("indexPx") or ctx.get("index_price") or ctx.get("midPx"))
    funding_rate = _to_float_allow_zero(ctx.get("funding") or ctx.get("funding_rate"))
    open_interest_usd = _to_float(ctx.get("openInterest") or ctx.get("open_interest_usd"))
    premium = _to_float(ctx.get("premium"))
    prev_day_price = _to_float(ctx.get("prevDayPx") or ctx.get("prev_day_price"))
    day_notional_volume = _to_float(ctx.get("dayNtlVlm") or ctx.get("day_notional_volume"))
    if ctx and mark_price is None:
        block_reasons.append("BLOCK_MARK_PRICE_MISSING")
    if ctx and oracle_price is None:
        block_reasons.append("BLOCK_ORACLE_PRICE_MISSING")
    if ctx and funding_rate is None:
        block_reasons.append("BLOCK_FUNDING_MISSING")
    if ctx and open_interest_usd is None:
        block_reasons.append("BLOCK_OPEN_INTEREST_MISSING")
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
        open_interest_usd=open_interest_usd,
        premium=premium,
        prev_day_price=prev_day_price,
        day_notional_volume=day_notional_volume,
        fee_mode=fee_mode or "unknown",
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
