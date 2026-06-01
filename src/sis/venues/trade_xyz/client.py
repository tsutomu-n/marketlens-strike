from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


class TradeXyzApiError(RuntimeError):
    pass


def _retryable_info_exception(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return True
    return (
        isinstance(exc, TradeXyzApiError)
        and bool(exc.args)
        and str(exc.args[0]).startswith(("info endpoint failed: 429", "info endpoint failed: 5"))
    )


@dataclass(frozen=True)
class TradeXyzClientConfig:
    base_url: str = "https://api.hyperliquid.xyz"
    dex: str = "xyz"
    timeout_seconds: float = 10.0
    transport: httpx.BaseTransport | None = None


class TradeXyzClient:
    def __init__(self, config: TradeXyzClientConfig | None = None) -> None:
        self.config = config or TradeXyzClientConfig()
        self._client = httpx.Client(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers={"content-type": "application/json"},
            transport=self.config.transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TradeXyzClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @retry(
        retry=retry_if_exception(_retryable_info_exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.25, min=0.25, max=2.0),
        reraise=True,
    )
    def post_info(self, payload: dict[str, Any]) -> Any:
        try:
            response = self._client.post("/info", json=payload)
        except (httpx.TimeoutException, httpx.TransportError):
            raise
        if response.status_code >= 400:
            raise TradeXyzApiError(
                f"info endpoint failed: {response.status_code} {response.text[:500]}"
            )
        return response.json()

    def all_mids(self, *, dex: str | None = None) -> dict[str, str]:
        payload = {"type": "allMids", "dex": dex or self.config.dex}
        data = self.post_info(payload)
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"allMids returned non-object: {type(data).__name__}")
        return {str(k): str(v) for k, v in data.items()}

    def clearinghouse_state(self, user: str) -> dict[str, Any]:
        data = self.post_info({"type": "clearinghouseState", "user": user})
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"clearinghouseState returned non-object: {type(data).__name__}")
        return data

    def open_orders(self, user: str, *, dex: str | None = None) -> list[dict[str, Any]]:
        data = self.post_info({"type": "openOrders", "user": user, "dex": dex or self.config.dex})
        if not isinstance(data, list):
            raise TradeXyzApiError(f"openOrders returned non-list: {type(data).__name__}")
        return [row for row in data if isinstance(row, dict)]

    def user_fills(self, user: str) -> list[dict[str, Any]]:
        data = self.post_info({"type": "userFills", "user": user})
        if not isinstance(data, list):
            raise TradeXyzApiError(f"userFills returned non-list: {type(data).__name__}")
        return [row for row in data if isinstance(row, dict)]

    def user_fills_by_time(
        self, user: str, *, start_time_ms: int, end_time_ms: int | None = None
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "type": "userFillsByTime",
            "user": user,
            "startTime": start_time_ms,
        }
        if end_time_ms is not None:
            payload["endTime"] = end_time_ms
        data = self.post_info(payload)
        if not isinstance(data, list):
            raise TradeXyzApiError(f"userFillsByTime returned non-list: {type(data).__name__}")
        return [row for row in data if isinstance(row, dict)]

    def user_fees(self, user: str) -> dict[str, Any]:
        data = self.post_info({"type": "userFees", "user": user})
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"userFees returned non-object: {type(data).__name__}")
        return data

    def funding_history(
        self, coin: str, *, start_time_ms: int, end_time_ms: int | None = None
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_time_ms,
        }
        if end_time_ms is not None:
            payload["endTime"] = end_time_ms
        data = self.post_info(payload)
        if not isinstance(data, list):
            raise TradeXyzApiError(f"fundingHistory returned non-list: {type(data).__name__}")
        return [row for row in data if isinstance(row, dict)]

    def order_status(
        self, *, user: str, oid: int | None = None, cloid: str | None = None
    ) -> dict[str, Any]:
        if oid is None and cloid is None:
            raise ValueError("order_status requires oid or cloid")
        oid_payload: int | str = oid if oid is not None else str(cloid)
        data = self.post_info({"type": "orderStatus", "user": user, "oid": oid_payload})
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"orderStatus returned non-object: {type(data).__name__}")
        return data

    def meta(self, *, dex: str | None = None) -> dict[str, Any]:
        data = self.post_info({"type": "meta", "dex": dex or self.config.dex})
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"meta returned non-object: {type(data).__name__}")
        return data

    def perp_dexs(self) -> list[Any]:
        data = self.post_info({"type": "perpDexs"})
        if not isinstance(data, list):
            raise TradeXyzApiError(f"perpDexs returned non-list: {type(data).__name__}")
        return data

    def meta_and_asset_ctxs(
        self, *, dex: str | None = None
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        data = self.post_info({"type": "metaAndAssetCtxs", "dex": dex or self.config.dex})
        if (
            not isinstance(data, list)
            or len(data) < 2
            or not isinstance(data[0], dict)
            or not isinstance(data[1], list)
        ):
            raise TradeXyzApiError(
                f"metaAndAssetCtxs returned unexpected payload: {type(data).__name__}"
            )
        return data[0], [row for row in data[1] if isinstance(row, dict)]

    def all_perp_metas(self) -> list[Any]:
        data = self.post_info({"type": "allPerpMetas"})
        if not isinstance(data, list):
            raise TradeXyzApiError(f"allPerpMetas returned non-list: {type(data).__name__}")
        return data

    def perps_at_open_interest_cap(self) -> list[Any]:
        data = self.post_info({"type": "perpsAtOpenInterestCap"})
        if not isinstance(data, list):
            raise TradeXyzApiError(
                f"perpsAtOpenInterestCap returned non-list: {type(data).__name__}"
            )
        return data

    def perp_dex_status(self, *, dex: str | None = None) -> dict[str, Any]:
        data = self.post_info({"type": "perpDexStatus", "dex": dex or self.config.dex})
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"perpDexStatus returned non-object: {type(data).__name__}")
        return data

    def perp_dex_limits(self, *, dex: str | None = None) -> dict[str, Any]:
        data = self.post_info({"type": "perpDexLimits", "dex": dex or self.config.dex})
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"perpDexLimits returned non-object: {type(data).__name__}")
        return data

    def l2_book(self, coin: str) -> dict[str, Any]:
        data = self.post_info({"type": "l2Book", "coin": coin})
        if not isinstance(data, dict):
            raise TradeXyzApiError(f"l2Book returned non-object: {type(data).__name__}")
        return data

    def candle_snapshot(
        self, coin: str, interval: str, start_ms: int, end_ms: int
    ) -> list[dict[str, Any]]:
        data = self.post_info(
            {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
                    "interval": interval,
                    "startTime": start_ms,
                    "endTime": end_ms,
                },
            }
        )
        if not isinstance(data, list):
            raise TradeXyzApiError(f"candleSnapshot returned non-list: {type(data).__name__}")
        return [row for row in data if isinstance(row, dict)]
