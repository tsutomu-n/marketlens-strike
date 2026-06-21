from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from typing import Any

import httpx


SENSITIVE_PARAM_NAMES = frozenset({"apikey", "api_key", "secret", "passphrase", "signature"})
QueryParamValue = str | int | float | bool | None


class BitgetResponseError(RuntimeError):
    def __init__(self, endpoint_id: str, message: str) -> None:
        super().__init__(f"{endpoint_id}: {message}")
        self.endpoint_id = endpoint_id
        self.message = message


@dataclass(frozen=True)
class BitgetPublicClientConfig:
    base_url: str
    timeout_seconds: float = 10.0
    max_retries: int = 2
    transport: httpx.AsyncBaseTransport | None = None

    def __post_init__(self) -> None:
        if not self.base_url.startswith("https://"):
            raise ValueError("Bitget public base_url must be https")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")


@dataclass(frozen=True)
class BitgetHTTPResult:
    endpoint_id: str
    method: str
    path: str
    params_redacted: dict[str, str]
    status_code: int
    headers: dict[str, str]
    payload: dict[str, Any]
    raw_text: str
    latency_ms: int
    received_at: datetime


class BitgetPublicClient:
    def __init__(self, config: BitgetPublicClientConfig) -> None:
        self.config = config

    @staticmethod
    def redact_params(params: Mapping[str, object]) -> dict[str, str]:
        redacted: dict[str, str] = {}
        for key, value in params.items():
            if key.lower() in SENSITIVE_PARAM_NAMES:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = str(value)
        return redacted

    async def get_json(
        self,
        *,
        endpoint_id: str,
        path: str,
        params: Mapping[str, QueryParamValue],
        expected_data_container: type[object] | None = None,
    ) -> BitgetHTTPResult:
        timeout = httpx.Timeout(self.config.timeout_seconds)
        base_url = self.config.base_url.rstrip("/")
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=self.config.transport,
        ) as client:
            return await self._get_json_with_client(
                client=client,
                endpoint_id=endpoint_id,
                path=path,
                params=params,
                expected_data_container=expected_data_container,
            )

    async def _get_json_with_client(
        self,
        *,
        client: httpx.AsyncClient,
        endpoint_id: str,
        path: str,
        params: Mapping[str, QueryParamValue],
        expected_data_container: type[object] | None,
    ) -> BitgetHTTPResult:
        last_transport_error: httpx.TimeoutException | httpx.TransportError | None = None
        for attempt in range(self.config.max_retries + 1):
            started = time.perf_counter()
            try:
                response = await client.get(path, params=dict(params))
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_transport_error = exc
                if attempt < self.config.max_retries:
                    continue
                raise BitgetResponseError(endpoint_id, exc.__class__.__name__) from exc

            latency_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < self.config.max_retries:
                    continue

            try:
                payload = response.json()
            except json.JSONDecodeError as exc:
                raise BitgetResponseError(endpoint_id, "response body is not valid JSON") from exc

            if not isinstance(payload, dict):
                raise BitgetResponseError(endpoint_id, "response JSON must be an object")

            if (
                200 <= response.status_code < 300
                and expected_data_container is not None
                and not isinstance(payload.get("data"), expected_data_container)
            ):
                raise BitgetResponseError(
                    endpoint_id,
                    f"response data must be {expected_data_container.__name__}",
                )

            return BitgetHTTPResult(
                endpoint_id=endpoint_id,
                method="GET",
                path=path,
                params_redacted=self.redact_params(params),
                status_code=response.status_code,
                headers={key.lower(): value for key, value in response.headers.items()},
                payload=payload,
                raw_text=response.text,
                latency_ms=latency_ms,
                received_at=datetime.now(timezone.utc).replace(microsecond=0),
            )

        if last_transport_error is not None:
            raise BitgetResponseError(endpoint_id, last_transport_error.__class__.__name__)
        raise BitgetResponseError(endpoint_id, "request failed without response")
