from datetime import datetime, timedelta, timezone

from sis.real_market.models import RealMarketBar, RealMarketFeature


def test_real_market_models_exist() -> None:
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
    feature = RealMarketFeature(
        ts=now,
        symbol="NVDA",
        timeframe="15m",
        close=bar.close,
        source_confidence=0.8,
        market_session="regular",
        event_flags=[],
    )
    assert bar.symbol == "NVDA"
    assert feature.market_session == "regular"
