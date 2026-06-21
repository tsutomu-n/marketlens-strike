from __future__ import annotations

import asyncio

import httpx
import pytest

from sis.crypto_perp.bitget.client import (
    BitgetPublicClient,
    BitgetPublicClientConfig,
    BitgetResponseError,
)


def _client(handler) -> BitgetPublicClient:
    return BitgetPublicClient(
        BitgetPublicClientConfig(
            base_url="https://api.bitget.com",
            transport=httpx.MockTransport(handler),
            max_retries=1,
        )
    )


def test_bitget_public_client_gets_json_with_params() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": "00000", "data": []})

    result = asyncio.run(
        _client(handler).get_json(
            endpoint_id="instruments",
            path="/api/v3/market/instruments",
            params={"category": "USDT-FUTURES"},
        )
    )

    assert result.status_code == 200
    assert result.payload == {"code": "00000", "data": []}
    assert requests[0].url.path == "/api/v3/market/instruments"
    assert requests[0].url.params["category"] == "USDT-FUTURES"


def test_bitget_public_client_retries_429_then_success() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"code": "429", "msg": "slow down"})
        return httpx.Response(200, json={"code": "00000", "data": []})

    result = asyncio.run(
        _client(handler).get_json(
            endpoint_id="tickers",
            path="/api/v3/market/tickers",
            params={"category": "USDT-FUTURES"},
        )
    )

    assert calls == 2
    assert result.status_code == 200


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"{not json"),
        httpx.Response(200, json={"code": "00000", "data": {"unexpected": []}}),
    ],
)
def test_bitget_public_client_does_not_retry_malformed_success(response: httpx.Response) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    with pytest.raises(BitgetResponseError):
        asyncio.run(
            _client(handler).get_json(
                endpoint_id="candles",
                path="/api/v3/market/candles",
                params={"category": "USDT-FUTURES", "symbol": "BTCUSDT"},
                expected_data_container=list,
            )
        )

    assert calls == 1


def test_bitget_public_client_redacts_params_for_artifacts() -> None:
    redacted = BitgetPublicClient.redact_params(
        {"category": "USDT-FUTURES", "apiKey": "secret", "symbol": "BTCUSDT"}
    )

    assert redacted["category"] == "USDT-FUTURES"
    assert redacted["symbol"] == "BTCUSDT"
    assert redacted["apiKey"] == "[REDACTED]"
