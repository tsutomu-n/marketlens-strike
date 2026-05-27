from datetime import datetime, timezone

from sis.models import MarketStatus, QuoteLog, SessionType, Venue
from sis.real_market.models import RealMarketFeature
from sis.tracking.real_vs_venue import build_tracking_record


def _quote(**kwargs) -> QuoteLog:
    base = {
        "ts_client": datetime.now(timezone.utc),
        "venue": Venue.TRADE_XYZ,
        "canonical_symbol": "NVDA",
        "venue_symbol": "NVDA",
        "source": "test",
        "raw_payload_sha256": "abc123",
        "mark_price": 100.0,
        "oracle_price": 100.0,
        "mid_price": 100.1,
        "best_bid": 100.0,
        "best_ask": 100.2,
        "spread_bps": 20.0,
        "depth_10bps_usd": 10000.0,
        "market_status": MarketStatus.OPEN,
        "session_type": SessionType.REGULAR,
        "is_tradable": True,
    }
    base.update(kwargs)
    return QuoteLog(**base)


def test_tracking_computes_mark_real_diff_bps() -> None:
    feature = RealMarketFeature(
        ts=datetime.now(timezone.utc),
        symbol="NVDA",
        timeframe="15m",
        close=101.0,
        source_confidence=0.9,
        market_session="regular",
    )
    row = build_tracking_record(feature, _quote(mark_price=102.0), {"halt_policy": {}})
    assert row.mark_real_diff_bps is not None
    assert row.mark_real_diff_bps > 0


def test_tracking_blocks_underlying_closed_session() -> None:
    feature = RealMarketFeature(
        ts=datetime.now(timezone.utc),
        symbol="NVDA",
        timeframe="15m",
        close=100.0,
        source_confidence=0.9,
        market_session="closed",
    )
    row = build_tracking_record(feature, _quote(), {"halt_policy": {}})
    assert row.trade_allowed is False
    assert "BLOCK_UNDERLYING_SESSION_CLOSED" in row.block_reasons


def test_tracking_blocks_low_source_confidence() -> None:
    feature = RealMarketFeature(
        ts=datetime.now(timezone.utc),
        symbol="NVDA",
        timeframe="15m",
        close=100.0,
        source_confidence=0.1,
        market_session="regular",
    )
    row = build_tracking_record(
        feature,
        _quote(),
        {"halt_policy": {"tracking": {"min_source_confidence": 0.7}}},
    )
    assert row.trade_allowed is False
    assert "BLOCK_LOW_SOURCE_CONFIDENCE" in row.block_reasons
