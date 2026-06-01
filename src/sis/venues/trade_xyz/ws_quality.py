from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.storage.jsonl_store import read_jsonl
from sis.storage.jsonl_store import write_json


def build_trade_xyz_ws_quality_manifest(
    *,
    data_dir: Path,
    raw_ws_root: Path,
    recv_gap_threshold_seconds: float = 60.0,
    source_gap_threshold_seconds: float = 60.0,
) -> dict[str, Any]:
    if recv_gap_threshold_seconds < 0:
        raise ValueError("recv_gap_threshold_seconds must be >= 0")
    if source_gap_threshold_seconds < 0:
        raise ValueError("source_gap_threshold_seconds must be >= 0")
    files = sorted(raw_ws_root.rglob("*.jsonl"))
    row_count = 0
    subscription_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    duplicate_payload_count = 0
    seen_payload_sha: set[str] = set()
    gap_count = 0
    max_gap_seconds = 0.0
    source_ts_gap_count = 0
    max_source_ts_gap_seconds = 0.0
    bbo_bid_ask_inversion_count = 0
    malformed_payload_count = 0
    unknown_symbol_count = 0
    subscription_response_count = 0
    pong_count = 0
    prev_recv_ts_ms: int | None = None
    prev_source_ts_ms: int | None = None
    for file in files:
        for row in read_jsonl(file):
            row_count += 1
            subscription = str(row.get("subscription") or "__missing__")
            subscription_counts[subscription] = subscription_counts.get(subscription, 0) + 1
            symbol = row.get("canonical_symbol")
            if isinstance(symbol, str):
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            elif row.get("message_kind") == "data":
                unknown_symbol_count += 1
            payload_sha = row.get("payload_sha256")
            if isinstance(payload_sha, str):
                if payload_sha in seen_payload_sha:
                    duplicate_payload_count += 1
                seen_payload_sha.add(payload_sha)
            recv_ts_ms = row.get("recv_ts_ms")
            if isinstance(recv_ts_ms, int) and prev_recv_ts_ms is not None:
                gap_s = max(0.0, (recv_ts_ms - prev_recv_ts_ms) / 1000.0)
                if gap_s > recv_gap_threshold_seconds:
                    gap_count += 1
                    max_gap_seconds = max(max_gap_seconds, gap_s)
            if isinstance(recv_ts_ms, int):
                prev_recv_ts_ms = recv_ts_ms
            source_ts_ms = row.get("source_ts_ms")
            if isinstance(source_ts_ms, int) and prev_source_ts_ms is not None:
                source_gap_s = max(0.0, (source_ts_ms - prev_source_ts_ms) / 1000.0)
                if source_gap_s > source_gap_threshold_seconds:
                    source_ts_gap_count += 1
                    max_source_ts_gap_seconds = max(max_source_ts_gap_seconds, source_gap_s)
            if isinstance(source_ts_ms, int):
                prev_source_ts_ms = source_ts_ms
            kind = str(row.get("message_kind") or "")
            if kind == "subscription_response":
                subscription_response_count += 1
            elif kind == "heartbeat":
                pong_count += 1
            payload = row.get("payload")
            if not isinstance(payload, dict):
                malformed_payload_count += 1
                continue
            channel = row.get("channel")
            if channel == "bbo":
                data = payload.get("data")
                if isinstance(data, dict):
                    bid = data.get("bidPx")
                    ask = data.get("askPx")
                    try:
                        if bid is not None and ask is not None and float(bid) > float(ask):
                            bbo_bid_ask_inversion_count += 1
                    except (TypeError, ValueError):
                        malformed_payload_count += 1
                else:
                    malformed_payload_count += 1
    block_reasons: list[str] = []
    if row_count == 0:
        block_reasons.append("empty_rows")
    if malformed_payload_count > 0:
        block_reasons.append("malformed_payload")
    if bbo_bid_ask_inversion_count > 0:
        block_reasons.append("bbo_bid_ask_inversion")
    if row_count == 0 or malformed_payload_count > 0 or bbo_bid_ask_inversion_count > 0:
        status = "fail"
    elif gap_count > 0 or source_ts_gap_count > 0:
        status = "warn"
    else:
        status = "pass"
    manifest = {
        "schema_version": "trade_xyz_ws_quality_manifest.v1",
        "source_manifest_path": str(data_dir / "manifests" / "trade_xyz_ws_capture_manifest.json"),
        "recv_gap_threshold_seconds": recv_gap_threshold_seconds,
        "source_gap_threshold_seconds": source_gap_threshold_seconds,
        "row_count": row_count,
        "subscription_counts": subscription_counts,
        "symbol_counts": symbol_counts,
        "duplicate_payload_count": duplicate_payload_count,
        "gap_count": gap_count,
        "max_gap_seconds": max_gap_seconds,
        "source_ts_gap_count": source_ts_gap_count,
        "max_source_ts_gap_seconds": max_source_ts_gap_seconds,
        "bbo_bid_ask_inversion_count": bbo_bid_ask_inversion_count,
        "malformed_payload_count": malformed_payload_count,
        "unknown_symbol_count": unknown_symbol_count,
        "subscription_response_count": subscription_response_count,
        "pong_count": pong_count,
        "status": status,
        "block_reasons": block_reasons,
    }
    write_json(data_dir / "manifests/trade_xyz_ws_quality_manifest.json", manifest)
    return manifest
