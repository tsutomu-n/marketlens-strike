from datetime import datetime, timedelta, timezone

from sis.real_market.models import RealMarketBar
from sis.real_market.quality import (
    estimate_source_confidence,
    live_suitability_reasons,
    source_confidence_reasons,
)


def test_source_confidence_blocks_yfinance_only_live() -> None:
    now = datetime(2026, 5, 26, 14, 0, tzinfo=timezone.utc)
    bar = RealMarketBar(
        ts_start=now - timedelta(minutes=15),
        ts_end=now,
        symbol="NVDA",
        timeframe="15m",
        open=100,
        high=101,
        low=99,
        close=100.5,
        volume=100000,
        source="yfinance",
    )
    score = estimate_source_confidence(bar, now=now, has_secondary_agreement=True)
    reasons = live_suitability_reasons(source_confidence=score, providers=["yfinance"])
    assert "BLOCK_YFINANCE_ONLY_LIVE" in reasons


def test_estimate_source_confidence_high_when_recent_and_complete() -> None:
    now = datetime(2026, 5, 26, 14, 0, tzinfo=timezone.utc)
    bar = RealMarketBar(
        ts_start=now - timedelta(minutes=15),
        ts_end=now,
        symbol="NVDA",
        timeframe="15m",
        open=100,
        high=101,
        low=99,
        close=100.5,
        volume=100000,
        source="alpaca",
    )
    score = estimate_source_confidence(bar, now=now, has_secondary_agreement=True)
    assert score >= 0.70
    assert source_confidence_reasons(score) == []
