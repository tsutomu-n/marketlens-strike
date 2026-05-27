from __future__ import annotations

from sis.models import QuoteLog
from sis.real_market.models import RealMarketFeature
from sis.tracking.models import TrackingRecord


def _diff_bps(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b <= 0:
        return None
    return abs(a - b) / b * 10_000


def build_tracking_record(
    feature: RealMarketFeature, quote: QuoteLog, policy: dict
) -> TrackingRecord:
    mark_diff = _diff_bps(quote.mark_price or quote.mid_price, feature.close)
    oracle_diff = _diff_bps(quote.oracle_price, feature.close)
    reasons: list[str] = []

    tracking_policy = policy.get("halt_policy", policy).get("tracking", {})
    spread_policy = policy.get("halt_policy", policy).get("spread", {}).get("max_spread_bps", {})
    min_source_conf = float(tracking_policy.get("min_source_confidence", 0.70))
    min_venue_quality = float(tracking_policy.get("min_venue_quality_score", 0.70))
    max_mark_real = float(
        tracking_policy.get("max_mark_real_diff_bps", {}).get("default_equity", 50)
    )

    if quote.mark_price is None:
        reasons.append("BLOCK_MISSING_MARK_PRICE")
    if quote.oracle_price is None:
        reasons.append("BLOCK_MISSING_ORACLE_PRICE")
    if feature.market_session != "regular":
        reasons.append("BLOCK_UNDERLYING_SESSION_CLOSED")
    if feature.source_confidence < min_source_conf:
        reasons.append("BLOCK_LOW_SOURCE_CONFIDENCE")
    if not quote.is_tradable:
        reasons.extend(quote.block_reasons or ["BLOCK_VENUE_NOT_TRADABLE"])

    default_spread = (
        float(spread_policy.get("default_equity", 25)) if isinstance(spread_policy, dict) else 25.0
    )
    symbol_spread = (
        float(spread_policy.get(quote.canonical_symbol, default_spread))
        if isinstance(spread_policy, dict)
        else default_spread
    )
    if quote.spread_bps is not None and quote.spread_bps > symbol_spread:
        reasons.append("BLOCK_SPREAD_TOO_WIDE")
    if mark_diff is not None and mark_diff > max_mark_real:
        reasons.append("BLOCK_MARK_REAL_DIVERGENCE")
    if oracle_diff is not None and oracle_diff > max_mark_real:
        reasons.append("BLOCK_ORACLE_REAL_DIVERGENCE")
    if quote.min_side_depth_10bps_usd is not None and quote.min_side_depth_10bps_usd <= 0:
        reasons.append("BLOCK_SIDE_DEPTH_TOO_THIN")
    if quote.fee_mode in (None, "unknown"):
        reasons.append("BLOCK_FEE_MODE_UNKNOWN")

    quality = 1.0
    if any(r == "BLOCK_SPREAD_TOO_WIDE" for r in reasons):
        quality -= 0.25
    if quote.depth_10bps_usd is None or quote.depth_10bps_usd <= 0:
        quality -= 0.25
    if mark_diff is None or mark_diff > max_mark_real:
        quality -= 0.25
    if feature.source_confidence < min_source_conf:
        quality -= 0.25
    quality = max(0.0, quality)
    if quality < min_venue_quality:
        reasons.append("BLOCK_LOW_VENUE_QUALITY")

    return TrackingRecord(
        ts_client=quote.ts_client,
        canonical_symbol=quote.canonical_symbol,
        venue=quote.venue.value,
        real_market_symbol=feature.symbol,
        real_price=feature.close,
        real_return_5m=feature.return_5m,
        real_return_15m=feature.return_15m,
        real_volume_zscore_15m=feature.volume_zscore_15m,
        realized_vol_15m=feature.realized_vol_15m,
        venue_mark=quote.mark_price,
        venue_oracle=quote.oracle_price,
        venue_mid=quote.mid_price,
        venue_best_bid=quote.best_bid,
        venue_best_ask=quote.best_ask,
        venue_spread_bps=quote.spread_bps,
        venue_depth_10bps_usd=quote.depth_10bps_usd,
        funding_rate=quote.funding_rate,
        mark_real_diff_bps=mark_diff,
        oracle_real_diff_bps=oracle_diff,
        source_confidence=feature.source_confidence,
        venue_quality_score=quality,
        trade_allowed=not reasons,
        block_reasons=list(dict.fromkeys(reasons)),
    )
