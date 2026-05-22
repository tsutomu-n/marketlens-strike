from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from sis.models import InstrumentSpec
from sis.venues.ostium.registry import OSTIUM_TARGETS

OSTIUM_PRICES_ENDPOINT = "https://builder.ostium.io/v1/prices"

TARGET_PAIR_ALIASES: dict[str, set[str]] = {
    "SPX_EQUIV": {"SPX-USD", "SPX/USD", "SPX"},
    "NDX_EQUIV": {"NDX-USD", "NDX/USD", "NDX"},
    "XAU": {"XAU-USD", "XAU/USD", "XAU"},
}


def _iter_price_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, dict):
        prices = payload.get("prices", payload.get("data", payload))
        if isinstance(prices, dict):
            for key, value in prices.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("pair", key)
                    yield item
            return
        if isinstance(prices, list):
            for item in prices:
                if isinstance(item, dict):
                    yield item


def _pair_key(item: dict[str, Any]) -> str | None:
    pair = item.get("pair") or item.get("symbol") or item.get("ticker")
    if isinstance(pair, str) and pair:
        return pair.upper()
    from_symbol = item.get("from")
    to_symbol = item.get("to")
    if isinstance(from_symbol, str) and isinstance(to_symbol, str):
        return f"{from_symbol}-{to_symbol}".upper()
    return None


def _price_index(payload: Any) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in _iter_price_items(payload):
        key = _pair_key(item)
        if key:
            indexed[key] = item
            indexed[key.replace("-", "/")] = item
    return indexed


def _resolve_target(target: InstrumentSpec, indexed: dict[str, dict[str, Any]]) -> InstrumentSpec:
    aliases = TARGET_PAIR_ALIASES.get(target.canonical_symbol, {target.canonical_symbol})
    for alias in aliases:
        item = indexed.get(alias.upper())
        if not item:
            continue
        pair = _pair_key(item) or alias.upper()
        notes = [
            "resolved via read-only Ostium Builder API GET /v1/prices",
            f"feed_id={item.get('feed_id')}",
            f"isMarketOpen={item.get('isMarketOpen')}",
        ]
        return target.model_copy(
            update={
                "venue_symbol": pair,
                "active": True,
                "api_readable": True,
                "api_orderable": False,
                "execution_price_ref": "bid/mid/ask from read-only price probe",
                "notes": notes,
            }
        )
    return target.model_copy(
        update={
            "active": False,
            "api_readable": False,
            "api_orderable": False,
            "notes": [*target.notes, "not found in Ostium Builder API GET /v1/prices"],
        }
    )


def probe_ostium_prices(
    *,
    endpoint: str = OSTIUM_PRICES_ENDPOINT,
    client: httpx.Client | None = None,
    targets: list[InstrumentSpec] | None = None,
) -> list[InstrumentSpec]:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    try:
        response = http_client.get(endpoint)
        response.raise_for_status()
        indexed = _price_index(response.json())
    finally:
        if owns_client:
            http_client.close()

    return [_resolve_target(target, indexed) for target in (targets or OSTIUM_TARGETS)]
