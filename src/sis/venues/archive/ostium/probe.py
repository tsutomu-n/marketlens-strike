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
from sis.venues.archive.ostium.registry import OSTIUM_TARGETS

OSTIUM_PRICES_ENDPOINT = "https://builder.ostium.io/v1/prices"

TARGET_PAIR_ALIASES: dict[str, set[str]] = {
    "SPX_EQUIV": {"SPX-USD", "SPX/USD", "SPX", "US500-USD", "US500/USD", "US500"},
    "NDX_EQUIV": {"NDX-USD", "NDX/USD", "NDX", "US100-USD", "US100/USD", "US100"},
    "XAU": {"XAU-USD", "XAU/USD", "XAU"},
}

OPENING_FEE_BPS_BY_CANONICAL_SYMBOL = {
    "SPX_EQUIV": 3,
    "NDX_EQUIV": 3,
    "XAU": 3,
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


def _iter_pair_metadata_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, dict):
        pairs = payload.get("pairs", payload.get("data", payload))
        if isinstance(pairs, list):
            for item in pairs:
                if isinstance(item, dict):
                    yield item


def _metadata_pair_key(item: dict[str, Any]) -> str | None:
    pair = item.get("venue_symbol") or item.get("pair") or item.get("symbol")
    if isinstance(pair, str) and pair:
        return pair.upper()
    pair_from = item.get("pair_from") or item.get("pairFrom") or item.get("from")
    pair_to = item.get("pair_to") or item.get("pairTo") or item.get("to")
    if isinstance(pair_from, str) and isinstance(pair_to, str):
        return f"{pair_from}-{pair_to}".upper()
    return None


def _metadata_index(payload: Any | None) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    if payload is None:
        return indexed
    for item in _iter_pair_metadata_items(payload):
        key = _metadata_pair_key(item)
        if key:
            indexed[key] = item
            indexed[key.replace("-", "/")] = item
    return indexed


def _matching_item(
    target: InstrumentSpec,
    indexed: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    aliases = TARGET_PAIR_ALIASES.get(target.canonical_symbol, {target.canonical_symbol})
    return next((indexed[alias.upper()] for alias in aliases if alias.upper() in indexed), None)


def _metadata_notes(
    target: InstrumentSpec,
    metadata: dict[str, Any] | None,
) -> list[str]:
    notes = [f"opening_fee_bps={OPENING_FEE_BPS_BY_CANONICAL_SYMBOL.get(target.canonical_symbol)}"]
    if not metadata:
        notes.append("pair metadata unavailable; run Ostium SDK sidecar getPairs")
        return notes
    for key in (
        "pair_id",
        "category",
        "max_leverage",
        "overnight_max_leverage",
        "rollover_fee_per_block",
        "rollover_rate_long",
        "rollover_rate_short",
        "open_interest",
        "buy_open_interest",
        "sell_open_interest",
        "max_open_interest",
        "is_market_open",
        "is_day_trading_closed",
        "seconds_to_toggle_is_day_trading_closed",
    ):
        if metadata.get(key) is not None:
            notes.append(f"{key}={metadata.get(key)}")
    notes.append("liquidation_reference=SDK open position liquidationPx; unavailable without position")
    return notes


def _float_metadata(metadata: dict[str, Any] | None, key: str) -> float | None:
    if not metadata:
        return None
    value = metadata.get(key)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _str_metadata(metadata: dict[str, Any] | None, key: str) -> str | None:
    if not metadata:
        return None
    value = metadata.get(key)
    if value is None:
        return None
    return str(value)


def _bool_metadata(metadata: dict[str, Any] | None, key: str) -> bool | None:
    if not metadata:
        return None
    value = metadata.get(key)
    return value if isinstance(value, bool) else None


def _int_metadata(metadata: dict[str, Any] | None, key: str) -> int | None:
    if not metadata:
        return None
    value = metadata.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.removeprefix("-").isdigit():
        return int(value)
    return None


def _metadata_pair_id(metadata: dict[str, Any] | None) -> int | None:
    if not metadata:
        return None
    value = metadata.get("pair_id")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _resolve_target(
    target: InstrumentSpec,
    indexed: dict[str, dict[str, Any]],
    metadata_index: dict[str, dict[str, Any]] | None = None,
) -> InstrumentSpec:
    aliases = TARGET_PAIR_ALIASES.get(target.canonical_symbol, {target.canonical_symbol})
    for alias in aliases:
        item = indexed.get(alias.upper())
        if not item:
            continue
        pair = _pair_key(item) or alias.upper()
        metadata = _matching_item(target.model_copy(update={"venue_symbol": pair}), metadata_index or {})
        notes = [
            "resolved via read-only Ostium Builder API GET /v1/prices",
            f"feed_id={item.get('feed_id')}",
            f"isMarketOpen={item.get('isMarketOpen')}",
            *_metadata_notes(target, metadata),
        ]
        return target.model_copy(
            update={
                "pair_id": _metadata_pair_id(metadata),
                "venue_symbol": pair,
                "active": True,
                "api_readable": True,
                "api_orderable": False,
                "execution_price_ref": "bid/mid/ask from read-only price probe",
                "opening_fee_bps": OPENING_FEE_BPS_BY_CANONICAL_SYMBOL.get(
                    target.canonical_symbol
                ),
                "rollover_fee_per_block": _str_metadata(metadata, "rollover_fee_per_block"),
                "rollover_rate_long": _str_metadata(metadata, "rollover_rate_long"),
                "rollover_rate_short": _str_metadata(metadata, "rollover_rate_short"),
                "open_interest": _str_metadata(metadata, "open_interest"),
                "buy_open_interest": _str_metadata(metadata, "buy_open_interest"),
                "sell_open_interest": _str_metadata(metadata, "sell_open_interest"),
                "max_open_interest": _str_metadata(metadata, "max_open_interest"),
                "max_leverage": _float_metadata(metadata, "max_leverage"),
                "overnight_max_leverage": _float_metadata(metadata, "overnight_max_leverage"),
                "trading_hours_ref": "Ostium getPairs isMarketOpen/isDayTradingClosed + Markets docs",
                "is_day_trading_closed": _bool_metadata(metadata, "is_day_trading_closed"),
                "seconds_to_toggle_is_day_trading_closed": _int_metadata(
                    metadata, "seconds_to_toggle_is_day_trading_closed"
                ),
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
    if not isinstance(bid, int | float):
        return None
    if not isinstance(ask, int | float):
        return None
    if not isinstance(mid, int | float):
        return None
    bid_value = float(bid)
    ask_value = float(ask)
    mid_value = float(mid)
    if mid_value == 0:
        return None
    return float((ask_value - bid_value) / mid_value * 10_000)


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
        raw_payload=item,
    )


def resolve_ostium_price_specs(
    payload: Any,
    *,
    pair_metadata_payload: Any | None = None,
    targets: list[InstrumentSpec] | None = None,
) -> list[InstrumentSpec]:
    indexed = _price_index(payload)
    metadata = _metadata_index(pair_metadata_payload)
    return [_resolve_target(target, indexed, metadata) for target in (targets or OSTIUM_TARGETS)]


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


def latest_pairs_metadata_file(root: Path) -> Path | None:
    paths = sorted(root.glob("pairs_*.json"))
    return paths[-1] if paths else None


def write_ostium_live_probe_outputs(
    *,
    data_dir: Path,
    endpoint: str = OSTIUM_PRICES_ENDPOINT,
    pairs_metadata_path: Path | None = None,
    client: httpx.Client | None = None,
) -> tuple[list[InstrumentSpec], list[QuoteLog]]:
    payload = _fetch_prices_payload(endpoint, client)
    if pairs_metadata_path is None:
        pairs_metadata_path = latest_pairs_metadata_file(data_dir / "raw/sidecar/ostium")
    pair_metadata_payload = (
        json.loads(pairs_metadata_path.read_text(encoding="utf-8"))
        if pairs_metadata_path and pairs_metadata_path.exists()
        else None
    )
    ts_client = datetime.now(timezone.utc)
    raw_payload_sha256 = _sha256_json(payload)
    raw_payload_ref = data_dir / "raw/payloads/ostium" / f"prices_{ts_client:%Y%m%d_%H%M%S}.json"
    write_json(raw_payload_ref, payload)

    specs = resolve_ostium_price_specs(payload, pair_metadata_payload=pair_metadata_payload)
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
