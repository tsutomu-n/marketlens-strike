from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sis.models import MarketStatus, QuoteLog, Venue
from sis.storage.jsonl_store import append_jsonl, read_jsonl


def latest_sidecar_file(sidecar_root: Path) -> Path:
    paths = sorted(sidecar_root.glob("*.jsonl"))
    if not paths:
        raise FileNotFoundError(f"No gTrade sidecar JSONL files found under {sidecar_root}")
    return paths[-1]


def latest_pricing_file(pricing_root: Path) -> Path:
    paths = sorted(pricing_root.glob("*.jsonl"))
    if not paths:
        raise FileNotFoundError(f"No gTrade pricing JSONL files found under {pricing_root}")
    return paths[-1]


def sidecar_market_status(snapshot: dict, pair_asset_class: str) -> tuple[MarketStatus, bool]:
    status = snapshot.get("market_status") or {}
    key = "isCommoditiesOpen" if pair_asset_class == "commodity" else "isIndicesOpen"
    is_open = status.get(key)
    if is_open is True:
        return MarketStatus.OPEN, True
    if is_open is False:
        return MarketStatus.CLOSED, False
    return MarketStatus.UNKNOWN, False


def sidecar_oracle_ts_ms(snapshot: dict) -> int | None:
    raw = snapshot.get("raw")
    if not isinstance(raw, dict):
        return None
    last_refreshed = raw.get("lastRefreshed")
    if not isinstance(last_refreshed, str) or not last_refreshed:
        return None
    return int(datetime.fromisoformat(last_refreshed.replace("Z", "+00:00")).timestamp() * 1000)


def quote_identity(row: dict) -> tuple[str | None, str | None, str | None]:
    return (
        row.get("ts_client"),
        row.get("canonical_symbol"),
        row.get("raw_payload_sha256"),
    )


def _parse_iso(ts: str | None) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _extract_pricing_rows(pricing_path: Path) -> dict[int, list[dict]]:
    by_pair_index: dict[int, list[dict]] = {}
    for snapshot in read_jsonl(pricing_path):
        ts_client = _parse_iso(snapshot.get("ts_client"))
        oracle_ts_ms = snapshot.get("oracle_ts_ms")
        if not isinstance(oracle_ts_ms, int):
            oracle_ts_ms = None
        for row in snapshot.get("prices", []):
            pair_index = row.get("pair_index")
            if not isinstance(pair_index, int):
                continue
            item = {
                "pair_index": pair_index,
                "mark_price": row.get("mark_price"),
                "index_price": row.get("index_price"),
                "oracle_ts_ms": oracle_ts_ms,
                "ts_client": ts_client,
                "raw_payload_sha256": snapshot.get("raw_payload_sha256"),
            }
            by_pair_index.setdefault(pair_index, []).append(item)
    return by_pair_index


def _closest_pricing_row(
    pair_index: int | None,
    ts_client: datetime,
    oracle_ts_ms: int | None,
    pricing_rows: dict[int, list[dict]] | None,
) -> dict | None:
    if pair_index is None or not pricing_rows:
        return None
    rows = pricing_rows.get(pair_index)
    if not rows:
        return None
    best: tuple[float, dict] | None = None
    for row in rows:
        row_oracle = row.get("oracle_ts_ms")
        if isinstance(oracle_ts_ms, int) and isinstance(row_oracle, int):
            delta_ms = abs(row_oracle - oracle_ts_ms)
        else:
            row_ts_client = row.get("ts_client")
            if not isinstance(row_ts_client, datetime):
                continue
            delta_ms = abs((row_ts_client - ts_client).total_seconds() * 1000)
        if delta_ms > 60_000:
            continue
        if best is None or delta_ms < best[0]:
            best = (delta_ms, row)
    return best[1] if best else None


def convert_sidecar_to_quote_logs(sidecar_path: Path, out_path: Path, pricing_path: Path | None = None) -> int:
    count = 0
    seen = {quote_identity(row) for row in read_jsonl(out_path)} if out_path.exists() else set()
    pricing_rows = _extract_pricing_rows(pricing_path) if pricing_path and pricing_path.exists() else None
    for snapshot in read_jsonl(sidecar_path):
        ts = datetime.fromisoformat(snapshot["ts_client"].replace("Z", "+00:00"))
        raw_hash = snapshot["raw_payload_sha256"]
        oracle_ts_ms = sidecar_oracle_ts_ms(snapshot)
        pairs_raw = snapshot.get("pairs")
        if pairs_raw is None:
            pairs_raw = snapshot.get("targets")
        if pairs_raw is None:
            pairs_raw = []

        if not isinstance(pairs_raw, list):
            raise TypeError("sidecar snapshot pairs/targets must be a list")

        for pair in pairs_raw:
            if not isinstance(pair, dict):
                raise TypeError("sidecar snapshot pair must be an object")

            pair_index_raw = pair.get("pair_index")
            if pair_index_raw is None:
                pair_index_raw = pair.get("pairIndex")
            if pair_index_raw is not None and not isinstance(pair_index_raw, int):
                raise TypeError("sidecar snapshot pair_index must be an int")
            pair_index = pair_index_raw

            asset_class_raw = pair.get("asset_class")
            if asset_class_raw is None:
                asset_class_raw = pair.get("assetClass")
            if asset_class_raw is None:
                asset_class = "unknown"
            elif isinstance(asset_class_raw, str):
                asset_class = asset_class_raw
            else:
                raise TypeError("sidecar snapshot asset_class must be a string")

            canonical_symbol_raw = pair.get("canonical_symbol")
            if canonical_symbol_raw is None:
                canonical_symbol_raw = pair.get("canonicalSymbol")
            if canonical_symbol_raw is None:
                raise ValueError("sidecar snapshot canonical_symbol is required")
            if not isinstance(canonical_symbol_raw, str):
                raise TypeError("sidecar snapshot canonical_symbol must be a string")
            canonical_symbol = canonical_symbol_raw

            venue_symbol_raw = pair.get("venue_symbol")
            if venue_symbol_raw is None:
                venue_symbol_raw = pair.get("venueSymbol")
            if venue_symbol_raw is None:
                raise ValueError("sidecar snapshot venue_symbol is required")
            if not isinstance(venue_symbol_raw, str):
                raise TypeError("sidecar snapshot venue_symbol must be a string")
            venue_symbol = venue_symbol_raw

            pricing_row = _closest_pricing_row(pair_index, ts, oracle_ts_ms, pricing_rows)
            market_status, is_tradable = sidecar_market_status(snapshot, asset_class)
            mark_price = pricing_row.get("mark_price") if pricing_row else None
            index_price = pricing_row.get("index_price") if pricing_row else None
            quote_oracle_ts_ms = (
                pricing_row.get("oracle_ts_ms") if pricing_row and pricing_row.get("oracle_ts_ms") is not None else oracle_ts_ms
            )
            quote = QuoteLog(
                ts_client=ts,
                venue=Venue.GTRADE,
                chain=snapshot.get("network", "arbitrum"),
                canonical_symbol=canonical_symbol,
                venue_symbol=venue_symbol,
                pair_index=pair_index,
                mark_price=mark_price,
                index_price=index_price,
                exec_buy_price=mark_price,
                exec_sell_price=mark_price,
                spread_bps=pair.get("spread_bps"),
                oracle_ts_ms=quote_oracle_ts_ms,
                market_status=market_status,
                is_tradable=is_tradable,
                source="gtrade_sidecar_v1_pricing_v4" if pricing_row else "gtrade_sidecar_v1",
                raw_payload_sha256=raw_hash,
                raw_payload_ref=str(sidecar_path),
                raw_payload={
                    "pair": pair,
                    "market_status": snapshot.get("market_status"),
                    "network": snapshot.get("network"),
                    "backend": snapshot.get("backend"),
                    "pricing": pricing_row,
                },
            )
            key = quote_identity(quote.model_dump(mode="json"))
            if key in seen:
                continue
            append_jsonl(out_path, quote)
            seen.add(key)
            count += 1
    return count
