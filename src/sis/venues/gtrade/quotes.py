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


def convert_sidecar_to_quote_logs(sidecar_path: Path, out_path: Path) -> int:
    count = 0
    for snapshot in read_jsonl(sidecar_path):
        ts = datetime.fromisoformat(snapshot["ts_client"].replace("Z", "+00:00"))
        raw_hash = snapshot["raw_payload_sha256"]
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
            append_jsonl(out_path, quote)
            count += 1
    return count
