from __future__ import annotations

import json

import httpx

from sis.venues.ostium.probe import probe_ostium_prices


def test_probe_ostium_prices_resolves_targets_from_builder_prices() -> None:
    payload = {
        "prices": [
            {
                "feed_id": "feed-spx",
                "pair": "SPX-USD",
                "from": "SPX",
                "to": "USD",
                "bid": 6000.1,
                "mid": 6000.2,
                "ask": 6000.3,
                "isMarketOpen": True,
            },
            {
                "feed_id": "feed-ndx",
                "pair": "NDX-USD",
                "from": "NDX",
                "to": "USD",
                "bid": 21000.1,
                "mid": 21000.2,
                "ask": 21000.3,
                "isMarketOpen": False,
            },
            {
                "feed_id": "feed-xau",
                "pair": "XAU-USD",
                "from": "XAU",
                "to": "USD",
                "bid": 3300.1,
                "mid": 3300.2,
                "ask": 3300.3,
                "isMarketOpen": True,
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://builder.ostium.io/v1/prices"
        return httpx.Response(200, content=json.dumps(payload).encode())

    client = httpx.Client(transport=httpx.MockTransport(handler))

    specs = probe_ostium_prices(client=client)

    by_symbol = {spec.canonical_symbol: spec for spec in specs}
    assert by_symbol["SPX_EQUIV"].venue_symbol == "SPX-USD"
    assert by_symbol["SPX_EQUIV"].active is True
    assert by_symbol["NDX_EQUIV"].venue_symbol == "NDX-USD"
    assert by_symbol["NDX_EQUIV"].active is True
    assert "isMarketOpen=False" in by_symbol["NDX_EQUIV"].notes
    assert by_symbol["XAU"].venue_symbol == "XAU-USD"
    assert by_symbol["XAU"].api_orderable is False
    assert "read-only" in by_symbol["XAU"].notes[0]
