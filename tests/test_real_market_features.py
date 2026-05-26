from datetime import datetime, timedelta, timezone

from sis.real_market.calendar import market_session
from sis.real_market.feature_builder import build_feature_from_bars
from sis.real_market.models import RealMarketBar


def _bars() -> list[RealMarketBar]:
    now = datetime(2026, 5, 26, 14, 0, tzinfo=timezone.utc)
    closes = [100.0, 100.5, 101.0, 100.8, 101.2]
    volumes = [1000, 1100, 900, 1200, 1500]
    rows = []
    for idx, (close, volume) in enumerate(zip(closes, volumes, strict=False)):
        end = now - timedelta(minutes=(len(closes) - 1 - idx) * 15)
        rows.append(
            RealMarketBar(
                ts_start=end - timedelta(minutes=15),
                ts_end=end,
                symbol="NVDA",
                timeframe="15m",
                open=close - 0.2,
                high=close + 0.3,
                low=close - 0.4,
                close=close,
                volume=volume,
                source="alpaca",
            )
        )
    return rows


def test_feature_builder_computes_return_and_volume_zscore() -> None:
    feature = build_feature_from_bars(_bars())
    assert feature.return_15m is not None
    assert feature.realized_vol_15m is not None
    assert feature.volume_zscore_15m is not None


def test_market_calendar_marks_regular_session() -> None:
    ts = datetime(2026, 5, 26, 14, 0, tzinfo=timezone.utc)
    assert market_session(ts) == "regular"


def test_event_flags_are_carried_to_feature() -> None:
    feature = build_feature_from_bars(_bars(), event_flags=["earnings"])
    assert feature.event_flags == ["earnings"]
