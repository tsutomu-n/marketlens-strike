from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.strategies.qqq_trend_rates_vix import build_qqq_trend_rates_vix_signals
from sis.strategies.sp500_trend_rates_vix import build_sp500_trend_rates_vix_signals


def test_build_qqq_trend_rates_vix_signals_generates_only_qqq_entries() -> None:
    frame = pl.DataFrame(
        [
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "canonical_symbol": "QQQ",
                "research_close": 100.0,
                "research_return_1d": 0.02,
                "research_return_4h": 0.01,
                "research_return_3d": 0.05,
                "sma_20": 95.0,
                "sma_50": 90.0,
                "close_above_sma20": True,
                "realized_vol_20": 1.0,
                "dgs10": 4.0,
                "dgs2": 3.0,
                "t10y2y": 1.0,
                "vix_level": 20.0,
                "dxy_proxy": 30.0,
                "is_event_blackout": False,
                "minutes_to_next_event": None,
                "minutes_since_last_event": None,
                "venue": "research",
                "venue_mark_price": None,
                "venue_index_price": None,
                "venue_spread_bps": None,
                "venue_stale_rate": None,
                "venue_tradable_rate": None,
                "trade_allowed": True,
                "blocked_reason": None,
            },
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "canonical_symbol": "SPY",
                "research_close": 100.0,
                "research_return_1d": 0.02,
                "research_return_4h": 0.01,
                "research_return_3d": 0.05,
                "sma_20": 95.0,
                "sma_50": 90.0,
                "close_above_sma20": True,
                "realized_vol_20": 1.0,
                "dgs10": 4.0,
                "dgs2": 3.0,
                "t10y2y": 1.0,
                "vix_level": 20.0,
                "dxy_proxy": 30.0,
                "is_event_blackout": False,
                "minutes_to_next_event": None,
                "minutes_since_last_event": None,
                "venue": "research",
                "venue_mark_price": None,
                "venue_index_price": None,
                "venue_spread_bps": None,
                "venue_stale_rate": None,
                "venue_tradable_rate": None,
                "trade_allowed": True,
                "blocked_reason": None,
            },
        ]
    )

    signals = build_qqq_trend_rates_vix_signals(frame)

    assert signals.height == 1
    assert signals.get_column("canonical_symbol").to_list() == ["QQQ"]
    assert signals.get_column("strategy_name").to_list() == ["qqq_trend_rates_vix"]
    assert signals.get_column("timeframe").to_list() == ["4h"]


def test_build_sp500_trend_rates_vix_signals_generates_only_spy_entries() -> None:
    frame = pl.DataFrame(
        [
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "canonical_symbol": "QQQ",
                "research_return_1d": 0.02,
                "close_above_sma20": True,
                "t10y2y": 1.0,
                "vix_level": 20.0,
                "is_event_blackout": False,
                "trade_allowed": True,
            },
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "canonical_symbol": "SPY",
                "research_return_1d": 0.02,
                "close_above_sma20": True,
                "t10y2y": 1.0,
                "vix_level": 20.0,
                "is_event_blackout": False,
                "trade_allowed": True,
            },
        ]
    )

    signals = build_sp500_trend_rates_vix_signals(frame)

    assert signals.height == 1
    assert signals.get_column("canonical_symbol").to_list() == ["SPY"]
    assert signals.get_column("strategy_name").to_list() == ["sp500_trend_rates_vix"]
    assert signals.get_column("timeframe").to_list() == ["4h"]
