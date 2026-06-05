from __future__ import annotations

import base64
import hashlib
import hmac

from sis.execution.base import OrderIntent
from sis.execution.bitget_demo_adapter import (
    BITGET_DEMO_PAPER_HEADER,
    BITGET_DEMO_PAPER_HEADER_VALUE,
    BitgetDemoAdapter,
    BitgetDemoCredentials,
    build_bitget_demo_headers,
    missing_bitget_demo_env,
    parse_bitget_demo_fill,
    parse_bitget_demo_order_status,
    sign_bitget_demo_request,
)


def test_bitget_demo_adapter_is_fail_closed_without_credentials() -> None:
    adapter = BitgetDemoAdapter.from_env({})

    healthcheck = adapter.healthcheck()

    assert healthcheck["available"] is False
    assert healthcheck["credential_status"] == "missing"
    assert healthcheck["missing_env"] == [
        "BITGET_DEMO_API_KEY",
        "BITGET_DEMO_API_SECRET",
        "BITGET_DEMO_PASSPHRASE",
    ]
    assert healthcheck["external_write_enabled"] is False
    assert healthcheck["exchange_write_used"] is False
    assert healthcheck["paptrading_header"] == "paptrading=1"


def test_bitget_demo_headers_include_paptrading_and_do_not_expose_secret() -> None:
    credentials = BitgetDemoCredentials(
        api_key="demo-key",
        api_secret="demo-secret",
        passphrase="demo-passphrase",
    )

    headers = build_bitget_demo_headers(
        credentials,
        timestamp_ms="1684814440729",
        method="get",
        request_path="/api/v2/mix/account/account",
        query_string="marginCoin=usdt&symbol=btcusdt",
    )

    assert headers[BITGET_DEMO_PAPER_HEADER] == BITGET_DEMO_PAPER_HEADER_VALUE
    assert headers["ACCESS-KEY"] == "demo-key"
    assert headers["ACCESS-PASSPHRASE"] == "demo-passphrase"
    assert "demo-secret" not in headers.values()
    assert headers["ACCESS-SIGN"] == sign_bitget_demo_request(
        api_secret="demo-secret",
        timestamp_ms="1684814440729",
        method="GET",
        request_path="/api/v2/mix/account/account",
        query_string="marginCoin=usdt&symbol=btcusdt",
    )


def test_bitget_demo_signature_matches_hmac_sha256_base64() -> None:
    expected = base64.b64encode(
        hmac.new(
            b"secret",
            b'123POST/api/v2/spot/trade/place-order{"symbol":"BTCUSDT"}',
            hashlib.sha256,
        ).digest()
    ).decode("ascii")

    actual = sign_bitget_demo_request(
        api_secret="secret",
        timestamp_ms="123",
        method="POST",
        request_path="/api/v2/spot/trade/place-order",
        body='{"symbol":"BTCUSDT"}',
    )

    assert actual == expected


def test_bitget_demo_estimate_and_write_methods_remain_non_writing() -> None:
    adapter = BitgetDemoAdapter.from_env(
        {
            "BITGET_DEMO_API_KEY": "key",
            "BITGET_DEMO_API_SECRET": "secret",
            "BITGET_DEMO_PASSPHRASE": "passphrase",
        }
    )

    estimate = adapter.estimate_order(
        OrderIntent(
            venue="bitget_demo",
            canonical_symbol="btcusdt",
            side="BUY",
            quantity=1.0,
            timeframe="4h",
        )
    )
    cancel = adapter.cancel_order("order-1")
    close = adapter.close_position("btcusdt", "long")

    assert adapter.healthcheck()["available"] is True
    assert estimate.venue == "bitget_demo"
    assert estimate.canonical_symbol == "BTCUSDT"
    assert "external_write_disabled" in estimate.notes
    assert cancel.success is False
    assert cancel.status == "external_write_disabled"
    assert close.success is False
    assert close.status == "external_write_disabled"


def test_bitget_demo_response_parsers_normalize_order_and_fill() -> None:
    order = parse_bitget_demo_order_status(
        {
            "data": {
                "orderId": "order-1",
                "symbol": "btcusdt",
                "side": "buy",
                "size": "0.2",
                "status": "live",
            }
        }
    )
    fill = parse_bitget_demo_fill(
        {
            "data": [
                {
                    "tradeId": "fill-1",
                    "orderId": "order-1",
                    "symbol": "btcusdt",
                    "side": "buy",
                    "size": "0.2",
                    "price": "65000.5",
                    "status": "filled",
                    "fillTime": "1710000000000",
                }
            ]
        }
    )

    assert order.venue == "bitget_demo"
    assert order.order_id == "order-1"
    assert order.canonical_symbol == "BTCUSDT"
    assert order.quantity == 0.2
    assert order.status == "live"
    assert fill.venue == "bitget_demo"
    assert fill.fill_id == "fill-1"
    assert fill.order_id == "order-1"
    assert fill.canonical_symbol == "BTCUSDT"
    assert fill.quantity == 0.2
    assert fill.price == 65000.5
    assert fill.ts_fill == "1710000000000"


def test_missing_bitget_demo_env_ignores_present_values() -> None:
    assert (
        missing_bitget_demo_env(
            {
                "BITGET_DEMO_API_KEY": "key",
                "BITGET_DEMO_API_SECRET": "secret",
                "BITGET_DEMO_PASSPHRASE": "passphrase",
            }
        )
        == []
    )
