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


def convert_sidecar_to_quote_logs(sidecar_path: Path, out_path: Path) -> int:
    count = 0
    seen = {quote_identity(row) for row in read_jsonl(out_path)} if out_path.exists() else set()
    for snapshot in read_jsonl(sidecar_path):
        ts = datetime.fromisoformat(snapshot["ts_client"].replace("Z", "+00:00"))
        raw_hash = snapshot["raw_payload_sha256"]
        oracle_ts_ms = sidecar_oracle_ts_ms(snapshot)
        for pair in snapshot.get("pairs", snapshot.get("targets", [])):
            market_status, is_tradable = sidecar_market_status(
                snapshot, pair.get("asset_class") or pair.get("assetClass") or "unknown"
            )
            quote = QuoteLog(
                ts_client=ts,
                venue=Venue.GTRADE,
                chain=snapshot.get("network", "arbitrum"),
                canonical_symbol=pair.get("canonical_symbol") or pair.get("canonicalSymbol"),
                venue_symbol=pair.get("venue_symbol") or pair.get("venueSymbol"),
                pair_index=pair.get("pair_index") or pair.get("pairIndex"),
                spread_bps=pair.get("spread_bps"),
                oracle_ts_ms=oracle_ts_ms,
                market_status=market_status,
                is_tradable=is_tradable,
                source="gtrade_sidecar_v1",
                raw_payload_sha256=raw_hash,
                raw_payload_ref=str(sidecar_path),
                raw_payload={
                    "pair": pair,
                    "market_status": snapshot.get("market_status"),
                    "network": snapshot.get("network"),
                    "backend": snapshot.get("backend"),
                },
            )
            key = quote_identity(quote.model_dump(mode="json"))
            if key in seen:
                continue
            append_jsonl(out_path, quote)
            seen.add(key)
            count += 1
    return count
