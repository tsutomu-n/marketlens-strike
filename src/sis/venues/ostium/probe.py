from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from sis.models import InstrumentSpec, MarketStatus, QuoteLog, Venue
from sis.storage.jsonl_store import append_jsonl, write_json
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


def _fetch_prices_payload(endpoint: str, client: httpx.Client | None) -> Any:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    try:
        response = http_client.get(endpoint)
        response.raise_for_status()
        return response.json()
    finally:
        if owns_client:
            http_client.close()


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _spread_bps(item: dict[str, Any]) -> float | None:
    bid = item.get("bid")
    ask = item.get("ask")
    mid = item.get("mid")
    if not all(isinstance(value, int | float) for value in (bid, ask, mid)):
        return None
    if mid == 0:
        return None
    return float((ask - bid) / mid * 10_000)


def _market_status(item: dict[str, Any]) -> tuple[MarketStatus, bool]:
    is_open = item.get("isMarketOpen") is True and item.get("isDayTradingClosed") is not True
    return (MarketStatus.OPEN, True) if is_open else (MarketStatus.CLOSED, False)


def _quote_for_target(
    target: InstrumentSpec,
    item: dict[str, Any],
    *,
    ts_client: datetime,
    raw_payload_sha256: str,
    raw_payload_ref: Path,
) -> QuoteLog:
    status, is_tradable = _market_status(item)
    timestamp_seconds = item.get("timestampSeconds")
    oracle_ts_ms = int(timestamp_seconds * 1000) if isinstance(timestamp_seconds, int | float) else None
    pair = _pair_key(item) or target.venue_symbol
    return QuoteLog(
        ts_client=ts_client,
        venue=Venue.OSTIUM,
        chain="arbitrum",
        canonical_symbol=target.canonical_symbol,
        venue_symbol=pair,
        oracle_price=item.get("mid") if isinstance(item.get("mid"), int | float) else None,
        bid_price=item.get("bid") if isinstance(item.get("bid"), int | float) else None,
        ask_price=item.get("ask") if isinstance(item.get("ask"), int | float) else None,
        mid_price=item.get("mid") if isinstance(item.get("mid"), int | float) else None,
        exec_buy_price=item.get("ask") if isinstance(item.get("ask"), int | float) else None,
        exec_sell_price=item.get("bid") if isinstance(item.get("bid"), int | float) else None,
        spread_bps=_spread_bps(item),
        oracle_ts_ms=oracle_ts_ms,
        market_status=status,
        is_tradable=is_tradable,
        source="ostium_builder_prices_v1",
        raw_payload_sha256=raw_payload_sha256,
        raw_payload_ref=str(raw_payload_ref),
    )


def resolve_ostium_price_specs(
    payload: Any,
    *,
    targets: list[InstrumentSpec] | None = None,
) -> list[InstrumentSpec]:
    indexed = _price_index(payload)
    return [_resolve_target(target, indexed) for target in (targets or OSTIUM_TARGETS)]


def build_ostium_quote_logs(
    payload: Any,
    *,
    ts_client: datetime,
    raw_payload_sha256: str,
    raw_payload_ref: Path,
    targets: list[InstrumentSpec] | None = None,
) -> list[QuoteLog]:
    indexed = _price_index(payload)
    quotes: list[QuoteLog] = []
    for target in targets or OSTIUM_TARGETS:
        aliases = TARGET_PAIR_ALIASES.get(target.canonical_symbol, {target.canonical_symbol})
        item = next((indexed[alias.upper()] for alias in aliases if alias.upper() in indexed), None)
        if item:
            quotes.append(
                _quote_for_target(
                    target,
                    item,
                    ts_client=ts_client,
                    raw_payload_sha256=raw_payload_sha256,
                    raw_payload_ref=raw_payload_ref,
                )
            )
    return quotes


def probe_ostium_prices(
    *,
    endpoint: str = OSTIUM_PRICES_ENDPOINT,
    client: httpx.Client | None = None,
    targets: list[InstrumentSpec] | None = None,
) -> list[InstrumentSpec]:
    payload = _fetch_prices_payload(endpoint, client)
    return resolve_ostium_price_specs(payload, targets=targets)


def write_ostium_live_probe_outputs(
    *,
    data_dir: Path,
    endpoint: str = OSTIUM_PRICES_ENDPOINT,
    client: httpx.Client | None = None,
) -> tuple[list[InstrumentSpec], list[QuoteLog]]:
    payload = _fetch_prices_payload(endpoint, client)
    ts_client = datetime.now(timezone.utc)
    raw_payload_sha256 = _sha256_json(payload)
    raw_payload_ref = data_dir / "raw/payloads/ostium" / f"prices_{ts_client:%Y%m%d_%H%M%S}.json"
    write_json(raw_payload_ref, payload)

    specs = resolve_ostium_price_specs(payload)
    quotes = build_ostium_quote_logs(
        payload,
        ts_client=ts_client,
        raw_payload_sha256=raw_payload_sha256,
        raw_payload_ref=raw_payload_ref,
    )
    quote_path = data_dir / "raw/quotes/ostium" / f"{ts_client.date().isoformat()}.jsonl"
    for quote in quotes:
        append_jsonl(quote_path, quote)
    return specs, quotes
