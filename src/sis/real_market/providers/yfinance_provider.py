from __future__ import annotations

from sis.real_market.models import RealMarketBar


def fetch_yfinance_bars(*, symbol: str, timeframe: str) -> list[RealMarketBar]:
    _ = (symbol, timeframe)
    return []
