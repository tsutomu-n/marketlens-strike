from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from sis.research.providers import PriceProvider, ResearchFetchRequest, YahooFinancePriceProvider

DEFAULT_PRICE_SYMBOLS = ["QQQ", "SPY", "GLD", "^VIX", "UUP", "USDJPY=X", "EURUSD=X"]


def build_market_panel(
    data_dir: Path,
    *,
    provider: PriceProvider | None = None,
    request: ResearchFetchRequest | None = None,
) -> Path:
    selected_provider = provider or YahooFinancePriceProvider()
    selected_request = request or ResearchFetchRequest(
        symbols=DEFAULT_PRICE_SYMBOLS,
        start=date.today() - timedelta(days=365),
        end=date.today() + timedelta(days=1),
        interval="1d",
    )
    frame = selected_provider.fetch_ohlcv(selected_request)
    if frame.is_empty():
        raise ValueError("No research price rows fetched.")

    raw_path = data_dir / "research/raw/yfinance_ohlcv.parquet"
    market_panel_path = data_dir / "research/market_panel.parquet"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    frame = frame.sort(["symbol", "ts"])
    frame.write_parquet(raw_path)
    frame.write_parquet(market_panel_path)
    return market_panel_path
