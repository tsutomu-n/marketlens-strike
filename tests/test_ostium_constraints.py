from __future__ import annotations

import json

import httpx

from sis.venues.archive.ostium import constraints


def test_write_ostium_constraint_artifact_distinguishes_market_close(
    tmp_path,
    monkeypatch,
) -> None:

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/latest-prices"):
            return httpx.Response(
                200,
                json={
                    "prices": [
                        {
                            "pair": "XAU-USD",
                            "from": "XAU",
                            "to": "USD",
                            "mid": 2400.0,
                            "bid": 2399.0,
                            "ask": 2401.0,
                            "isMarketOpen": False,
                            "isDayTradingClosed": False,
                            "timestampSeconds": 1779408000,
                        }
                    ]
                },
            )
        if request.url.path.endswith("/v1/prices"):
            return httpx.Response(
                200,
                json={
                    "prices": [
                        {
                            "pair": "XAU-USD",
                            "from": "XAU",
                            "to": "USD",
                            "mid": 2400.0,
                            "bid": 2399.0,
                            "ask": 2401.0,
                            "isMarketOpen": False,
                        }
                    ]
                },
            )
        if request.url.path.endswith("/latest-price"):
            assert request.url.params["asset"] == "XAUUSD"
            return httpx.Response(200, json={"from": "XAU", "to": "USD", "mid": 2400.0})
        if request.url.path.endswith("/asset-schedule"):
            assert request.url.params["asset"] == "XAUUSD"
            return httpx.Response(
                200, json={"asset": request.url.params["asset"], "marketOpen": False}
            )
        raise AssertionError(str(request.url))

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://example.test")

    result = constraints.write_ostium_constraint_artifact(
        data_dir=tmp_path,
        run_id="r1",
        assets=("XAU",),
        latest_prices_endpoint="https://example.test/PricePublish/latest-prices",
        latest_price_endpoint="https://example.test/PricePublish/latest-price",
        trading_hours_endpoint="https://example.test/trading-hours/asset-schedule",
        builder_prices_endpoint="https://example.test/v1/prices",
        client=client,
        sdk_probe=lambda: {
            "available": True,
            "version": "3.2.1",
            "status": "read_only_probe_passed",
            "method": "price.get_latest_prices",
            "observed_count": 1,
            "private_key_used": False,
            "notes": ["python_sdk_read_only_probe_passed"],
        },
    )

    assert result["constraint_status"] == "pass"
    assert result["assets"][0]["market_state"] == "closed"
    assert result["assets"][0]["market_close_is_missing_data"] is False
    payload = json.loads((tmp_path / "ops/ostium_constraints_r1.json").read_text())
    assert payload["python_sdk"]["status"] == "read_only_probe_passed"
    assert payload["builder_prices_artifact"]["path"].endswith("_builder_prices.json")
    assert payload["assets"][0]["legacy_asset_param"] == "XAUUSD"
    assert payload["slippage_rule"]["non_market_open_trade_slippage_required"] == 0


def test_write_ostium_constraint_artifact_fails_closed_without_python_sdk(
    tmp_path,
    monkeypatch,
) -> None:
    def missing(name: str) -> str:
        raise constraints.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(constraints.importlib.metadata, "version", missing)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/latest-prices"):
            return httpx.Response(
                200,
                json={
                    "prices": [
                        {
                            "pair": "XAU-USD",
                            "from": "XAU",
                            "to": "USD",
                            "mid": 2400.0,
                            "bid": 2399.0,
                            "ask": 2401.0,
                            "isMarketOpen": True,
                        }
                    ]
                },
            )
        if request.url.path.endswith("/v1/prices"):
            return httpx.Response(
                200,
                json={
                    "prices": [{"pair": "XAU-USD", "from": "XAU", "to": "USD", "bid": 1, "ask": 2}]
                },
            )
        return httpx.Response(200, json={"asset": request.url.params.get("asset", "XAUUSD")})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://example.test")

    result = constraints.write_ostium_constraint_artifact(
        data_dir=tmp_path,
        run_id="r2",
        assets=("XAU",),
        latest_prices_endpoint="https://example.test/PricePublish/latest-prices",
        latest_price_endpoint="https://example.test/PricePublish/latest-price",
        trading_hours_endpoint="https://example.test/trading-hours/asset-schedule",
        builder_prices_endpoint="https://example.test/v1/prices",
        client=client,
    )

    assert result["constraint_status"] == "failed"
    assert "python_sdk_read_only_probe_failed" in result["failures"]
