from __future__ import annotations

import json

import httpx
import pytest

from sis.venues.trade_xyz.client import TradeXyzApiError, TradeXyzClient, TradeXyzClientConfig


def _client_for_responses(responses: dict[str, object]) -> tuple[TradeXyzClient, list[dict]]:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        requests.append(payload)
        response = responses[payload["type"]]
        return httpx.Response(200, json=response)

    client = TradeXyzClient(
        TradeXyzClientConfig(
            base_url="https://example.test",
            transport=httpx.MockTransport(handler),
        )
    )
    return client, requests


def test_trade_xyz_client_read_only_execution_state_methods() -> None:
    client, requests = _client_for_responses(
        {
            "clearinghouseState": {"marginSummary": {"accountValue": "1000"}},
            "openOrders": [{"coin": "xyz:SP500", "oid": 1}],
            "userFills": [{"coin": "xyz:SP500", "px": "100"}],
            "userFillsByTime": [{"coin": "xyz:SP500", "px": "101"}],
            "userFees": {"userCrossRate": "0.000315", "userAddRate": "0.000105"},
            "orderStatus": {"status": "open", "order": {"oid": 1}},
            "perpsAtOpenInterestCap": [],
            "perpDexStatus": {"status": "ok"},
            "perpDexLimits": {"limits": {}},
        }
    )

    try:
        assert client.clearinghouse_state("0xabc")["marginSummary"]["accountValue"] == "1000"
        assert client.open_orders("0xabc") == [{"coin": "xyz:SP500", "oid": 1}]
        assert client.user_fills("0xabc") == [{"coin": "xyz:SP500", "px": "100"}]
        assert client.user_fills_by_time(
            "0xabc", start_time_ms=1_700_000_000_000, end_time_ms=1_700_000_060_000
        ) == [{"coin": "xyz:SP500", "px": "101"}]
        assert client.user_fees("0xabc") == {
            "userCrossRate": "0.000315",
            "userAddRate": "0.000105",
        }
        assert client.order_status(user="0xabc", cloid="0xcloid")["status"] == "open"
        assert client.perps_at_open_interest_cap() == []
        assert client.perp_dex_status()["status"] == "ok"
        assert "limits" in client.perp_dex_limits()
    finally:
        client.close()

    assert requests == [
        {"type": "clearinghouseState", "user": "0xabc"},
        {"type": "openOrders", "user": "0xabc", "dex": "xyz"},
        {"type": "userFills", "user": "0xabc"},
        {
            "type": "userFillsByTime",
            "user": "0xabc",
            "startTime": 1_700_000_000_000,
            "endTime": 1_700_000_060_000,
        },
        {"type": "userFees", "user": "0xabc"},
        {"type": "orderStatus", "user": "0xabc", "oid": "0xcloid"},
        {"type": "perpsAtOpenInterestCap"},
        {"type": "perpDexStatus", "dex": "xyz"},
        {"type": "perpDexLimits", "dex": "xyz"},
    ]


def test_trade_xyz_client_read_only_methods_reject_unexpected_shapes() -> None:
    client, _requests = _client_for_responses({"openOrders": {"not": "a-list"}})

    try:
        with pytest.raises(TradeXyzApiError, match="openOrders returned non-list"):
            client.open_orders("0xabc")
    finally:
        client.close()


def test_trade_xyz_client_order_status_requires_identifier() -> None:
    client, _requests = _client_for_responses({})

    try:
        with pytest.raises(ValueError, match="requires oid or cloid"):
            client.order_status(user="0xabc")
    finally:
        client.close()


def test_trade_xyz_client_does_not_retry_non_retryable_4xx() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        _ = request
        return httpx.Response(400, text="bad request")

    client = TradeXyzClient(
        TradeXyzClientConfig(
            base_url="https://example.test",
            transport=httpx.MockTransport(handler),
        )
    )

    try:
        with pytest.raises(TradeXyzApiError, match="info endpoint failed: 400"):
            client.post_info({"type": "openOrders", "user": "0xabc"})
    finally:
        client.close()

    assert calls == 1
