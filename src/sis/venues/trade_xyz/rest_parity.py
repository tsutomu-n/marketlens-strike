from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any

from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.client import TradeXyzClient


def _ctx_symbols_from_meta(meta: Any, ctxs: list[Any]) -> set[str]:
    if not isinstance(meta, dict):
        return set()
    universe = meta.get("universe")
    if not isinstance(universe, list):
        return set()
    symbols: set[str] = set()
    for index, ctx in enumerate(ctxs):
        if not isinstance(ctx, dict) or index >= len(universe):
            continue
        item = universe[index]
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.startswith("xyz:"):
            symbols.add(name.removeprefix("xyz:").upper())
    return symbols


def build_trade_xyz_rest_parity_manifest(
    *,
    data_dir: Path,
    ws_manifest_path: Path,
    symbols: list[str],
    client: TradeXyzClient,
    request_delay_seconds: float = 0.2,
    include_l2_book: bool = False,
    l2_max_symbols: int = 3,
) -> dict[str, Any]:
    ws_manifest = {}
    if ws_manifest_path.exists():
        import json

        ws_manifest = json.loads(ws_manifest_path.read_text(encoding="utf-8"))
    started = datetime.now(tz=UTC)
    request_count = 0
    request_error_count = 0
    rate_limit_sleep_seconds = 0.0
    block_reasons: list[str] = []
    missing_ws_symbols: list[str] = []
    missing_rest_symbols: list[str] = []
    mismatched_symbols: list[str] = []
    known_gaps: list[str] = []

    try:
        mids = client.all_mids()
        request_count += 1
    except Exception:
        mids = {}
        request_error_count += 1
        block_reasons.append("allMids_request_error")
    try:
        meta, ctxs = client.meta_and_asset_ctxs()
        request_count += 1
    except Exception:
        meta = {}
        ctxs = []
        request_error_count += 1
        block_reasons.append("metaAndAssetCtxs_request_error")

    for endpoint in ("perps_at_open_interest_cap", "perp_dex_status", "perp_dex_limits"):
        try:
            getattr(client, endpoint)()
            request_count += 1
        except Exception:
            known_gaps.append(f"{endpoint}_unavailable")

    if include_l2_book:
        for symbol in symbols[: max(0, l2_max_symbols)]:
            coin = f"xyz:{symbol}"
            try:
                _ = client.l2_book(coin)
                request_count += 1
            except Exception:
                request_error_count += 1
                known_gaps.append(f"l2Book_error:{symbol}")
            sleep(request_delay_seconds)
            rate_limit_sleep_seconds += request_delay_seconds

    ws_symbols = {
        str(item).upper()
        for item in ws_manifest.get("symbols", [])
        if isinstance(item, str) and item.strip()
    }
    requested_symbols = {item.upper() for item in symbols}
    mid_symbols = {
        str(key).removeprefix("xyz:").upper()
        for key in mids.keys()
        if isinstance(key, str) and str(key).startswith("xyz:")
    }
    ctx_symbols = {
        str(item.get("coin")).removeprefix("xyz:").upper()
        for item in ctxs
        if isinstance(item, dict) and isinstance(item.get("coin"), str)
    }
    ctx_symbols |= _ctx_symbols_from_meta(meta, ctxs)
    rest_symbols = mid_symbols | ctx_symbols
    for symbol in sorted(requested_symbols):
        if ws_symbols and symbol not in ws_symbols:
            missing_ws_symbols.append(symbol)
        if symbol not in rest_symbols:
            missing_rest_symbols.append(symbol)
    for symbol in sorted(requested_symbols):
        in_mid = symbol in mid_symbols
        in_ctx = symbol in ctx_symbols
        if in_mid != in_ctx:
            mismatched_symbols.append(symbol)

    ended = datetime.now(tz=UTC)
    if request_error_count > 0:
        status = "warn"
    else:
        status = "pass"
    if missing_rest_symbols or missing_ws_symbols:
        status = "warn"
    if len(missing_rest_symbols) == len(requested_symbols) and requested_symbols:
        status = "fail"
        block_reasons.append("all_symbols_missing_from_rest")

    manifest = {
        "schema_version": "trade_xyz_rest_parity_manifest.v1",
        "source": "hyperliquid_info",
        "dex": "xyz",
        "symbols": sorted(requested_symbols),
        "window_start": started.isoformat(),
        "window_end": ended.isoformat(),
        "rest_endpoints": [
            "allMids",
            "metaAndAssetCtxs",
            "perpsAtOpenInterestCap",
            "perpDexStatus",
            "perpDexLimits",
        ],
        "ws_manifest_path": str(ws_manifest_path),
        "comparison_count": len(requested_symbols),
        "missing_ws_symbols": missing_ws_symbols,
        "missing_rest_symbols": missing_rest_symbols,
        "mismatched_symbols": mismatched_symbols,
        "rate_limit_sleep_seconds": rate_limit_sleep_seconds,
        "request_error_count": request_error_count,
        "request_count": request_count,
        "status": status,
        "block_reasons": block_reasons,
        "known_gaps": known_gaps,
        "known_gap_count": len(known_gaps),
    }
    write_json(data_dir / "manifests/trade_xyz_rest_parity_manifest.json", manifest)
    return manifest
