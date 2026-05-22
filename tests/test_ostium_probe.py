from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx

from sis.venues.ostium.probe import (
    build_ostium_quote_logs,
    resolve_ostium_price_specs,
    probe_ostium_prices,
)


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


def test_build_ostium_quote_logs_preserves_price_references() -> None:
    payload = {
        "prices": [
            {
                "feed_id": "feed-xau",
                "pair": "XAU-USD",
                "from": "XAU",
                "to": "USD",
                "bid": 3300.1,
                "mid": 3300.2,
                "ask": 3300.3,
                "isMarketOpen": True,
                "isDayTradingClosed": False,
                "timestampSeconds": 1779415479,
            }
        ]
    }

    quotes = build_ostium_quote_logs(
        payload,
        ts_client=datetime.fromisoformat("2026-05-22T00:00:00+00:00"),
        raw_payload_sha256="abc123",
        raw_payload_ref=Path("data/raw/payloads/ostium/prices.json"),
    )

    assert len(quotes) == 1
    quote = quotes[0]
    assert quote.canonical_symbol == "XAU"
    assert quote.venue_symbol == "XAU-USD"
    assert quote.bid_price == 3300.1
    assert quote.ask_price == 3300.3
    assert quote.exec_buy_price == 3300.3
    assert quote.exec_sell_price == 3300.1
    assert quote.oracle_ts_ms == 1779415479000
    assert quote.is_tradable is True
    assert quote.raw_payload == payload["prices"][0]


def test_resolve_ostium_price_specs_merges_pair_metadata() -> None:
    price_payload = {
        "prices": [
            {
                "feed_id": "feed-us500",
                "pair": "US500-USD",
                "from": "US500",
                "to": "USD",
                "bid": 6000.1,
                "mid": 6000.2,
                "ask": 6000.3,
                "isMarketOpen": True,
            }
        ]
    }
    pair_payload = {
        "pairs": [
            {
                "pair_id": "42",
                "venue_symbol": "US500-USD",
                "category": "indices",
                "max_leverage": 200,
                "overnight_max_leverage": 50,
                "rollover_fee_per_block": "123",
                "rollover_rate_long": "0.01",
                "rollover_rate_short": "-0.02",
                "open_interest": "1000",
                "buy_open_interest": "600",
                "sell_open_interest": "400",
                "max_open_interest": "5000",
                "is_market_open": True,
            }
        ]
    }

    specs = resolve_ostium_price_specs(price_payload, pair_metadata_payload=pair_payload)
    spx = {spec.canonical_symbol: spec for spec in specs}["SPX_EQUIV"]

    assert spx.venue_symbol == "US500-USD"
    assert spx.pair_id == 42
    assert spx.opening_fee_bps == 3
    assert spx.max_leverage == 200
    assert spx.max_open_interest == "5000"
    assert spx.rollover_fee_per_block == "123"
    assert "opening_fee_bps=3" in spx.notes
    assert "max_open_interest=5000" in spx.notes
    assert "rollover_fee_per_block=123" in spx.notes
