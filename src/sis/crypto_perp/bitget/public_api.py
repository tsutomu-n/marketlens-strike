from __future__ import annotations

from sis.crypto_perp.bitget.client import BitgetHTTPResult, BitgetPublicClient


INSTRUMENTS_PATH = "/api/v3/market/instruments"
TICKERS_PATH = "/api/v3/market/tickers"
CANDLES_PATH = "/api/v3/market/candles"
OPEN_INTEREST_PATH = "/api/v3/market/open-interest"
FUNDING_HISTORY_PATH = "/api/v3/market/history-fund-rate"


class BitgetPublicAPI:
    def __init__(self, client: BitgetPublicClient, *, category: str) -> None:
        self._client = client
        self._category = category

    async def instruments(self) -> BitgetHTTPResult:
        return await self._client.get_json(
            endpoint_id="instruments",
            path=INSTRUMENTS_PATH,
            params={"category": self._category},
            expected_data_container=list,
        )

    async def tickers(self) -> BitgetHTTPResult:
        return await self._client.get_json(
            endpoint_id="tickers",
            path=TICKERS_PATH,
            params={"category": self._category},
            expected_data_container=list,
        )

    async def candles(
        self, *, symbol: str, interval: str = "15m", limit: int = 100
    ) -> BitgetHTTPResult:
        return await self._client.get_json(
            endpoint_id="candles",
            path=CANDLES_PATH,
            params={
                "category": self._category,
                "symbol": symbol,
                "interval": interval,
                "type": "market",
                "limit": limit,
            },
            expected_data_container=list,
        )

    async def open_interest(self, *, symbol: str) -> BitgetHTTPResult:
        return await self._client.get_json(
            endpoint_id="open_interest",
            path=OPEN_INTEREST_PATH,
            params={"category": self._category, "symbol": symbol},
            expected_data_container=dict,
        )

    async def funding_history(self, *, symbol: str, limit: int = 100) -> BitgetHTTPResult:
        return await self._client.get_json(
            endpoint_id="funding_history",
            path=FUNDING_HISTORY_PATH,
            params={"category": self._category, "symbol": symbol, "limit": limit},
            expected_data_container=dict,
        )
