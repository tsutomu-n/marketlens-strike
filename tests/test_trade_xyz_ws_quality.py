from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from sis.storage.jsonl_store import append_jsonl
from sis.venues.trade_xyz.ws_quality import build_trade_xyz_ws_quality_manifest


def test_build_trade_xyz_ws_quality_manifest(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    raw_root = data_dir / "raw/ws/trade_xyz/date=2026-06-01/subscription=bbo/symbol=SP500"
    row_path = raw_root / "part-000001.jsonl"
    append_jsonl(
        row_path,
        {
            "schema_version": "trade_xyz_ws_raw.v1",
            "source": "hyperliquid_ws",
            "source_tier": "official_ws",
            "dex": "xyz",
            "ws_url": "wss://api.hyperliquid.xyz/ws",
            "channel": "bbo",
            "message_kind": "data",
            "subscription": "bbo",
            "subscription_hash": "sha256:a",
            "connection_id": "c1",
            "sequence": 1,
            "recv_ts_ms": 1700000000000,
            "recv_monotonic_ns": 1,
            "canonical_symbol": "SP500",
            "payload_sha256": "sha256:p1",
            "payload": {"channel": "bbo", "data": {"bidPx": "99.9", "askPx": "100.1"}},
        },
    )
    append_jsonl(
        row_path,
        {
            "schema_version": "trade_xyz_ws_raw.v1",
            "source": "hyperliquid_ws",
            "source_tier": "official_ws",
            "dex": "xyz",
            "ws_url": "wss://api.hyperliquid.xyz/ws",
            "channel": "subscriptionResponse",
            "message_kind": "subscription_response",
            "subscription": "__control__",
            "subscription_hash": "sha256:b",
            "connection_id": "c1",
            "sequence": 2,
            "recv_ts_ms": 1700000001000,
            "recv_monotonic_ns": 2,
            "payload_sha256": "sha256:p2",
            "payload": {"channel": "subscriptionResponse", "data": {"ok": True}},
        },
    )
    manifest = build_trade_xyz_ws_quality_manifest(
        data_dir=data_dir, raw_ws_root=data_dir / "raw/ws/trade_xyz"
    )
    assert manifest["row_count"] == 2
    assert manifest["status"] == "pass"
    assert manifest["gap_count"] == 0
    assert manifest["subscription_response_count"] == 1
    assert manifest["bbo_bid_ask_inversion_count"] == 0
    schema = json.loads(
        Path("schemas/trade_xyz_ws_quality_manifest.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=manifest, schema=schema)


def test_build_trade_xyz_ws_quality_manifest_warns_on_threshold_gap(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    raw_root = data_dir / "raw/ws/trade_xyz/date=2026-06-01/subscription=bbo/symbol=SP500"
    row_path = raw_root / "part-000001.jsonl"
    base_row = {
        "schema_version": "trade_xyz_ws_raw.v1",
        "source": "hyperliquid_ws",
        "source_tier": "official_ws",
        "dex": "xyz",
        "ws_url": "wss://api.hyperliquid.xyz/ws",
        "channel": "bbo",
        "message_kind": "data",
        "subscription": "bbo",
        "subscription_hash": "sha256:a",
        "connection_id": "c1",
        "recv_monotonic_ns": 1,
        "canonical_symbol": "SP500",
        "payload": {"channel": "bbo", "data": {"bidPx": "99.9", "askPx": "100.1"}},
    }
    append_jsonl(
        row_path,
        {
            **base_row,
            "sequence": 1,
            "recv_ts_ms": 1700000000000,
            "source_ts_ms": 1700000000000,
            "payload_sha256": "sha256:p1",
        },
    )
    append_jsonl(
        row_path,
        {
            **base_row,
            "sequence": 2,
            "recv_ts_ms": 1700000121000,
            "source_ts_ms": 1700000121000,
            "payload_sha256": "sha256:p2",
        },
    )
    manifest = build_trade_xyz_ws_quality_manifest(
        data_dir=data_dir, raw_ws_root=data_dir / "raw/ws/trade_xyz"
    )
    assert manifest["status"] == "warn"
    assert manifest["gap_count"] == 1
    assert manifest["source_ts_gap_count"] == 1


def test_build_trade_xyz_ws_quality_manifest_does_not_gap_across_streams(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    aapl_path = (
        data_dir / "raw/ws/trade_xyz/date=2026-06-01/subscription=bbo/symbol=AAPL/part-000001.jsonl"
    )
    sp500_path = (
        data_dir
        / "raw/ws/trade_xyz/date=2026-06-01/subscription=bbo/symbol=SP500/part-000001.jsonl"
    )
    base_row = {
        "schema_version": "trade_xyz_ws_raw.v1",
        "source": "hyperliquid_ws",
        "source_tier": "official_ws",
        "dex": "xyz",
        "ws_url": "wss://api.hyperliquid.xyz/ws",
        "channel": "bbo",
        "message_kind": "data",
        "subscription": "bbo",
        "subscription_hash": "sha256:a",
        "connection_id": "c1",
        "recv_monotonic_ns": 1,
        "payload": {"channel": "bbo", "data": {"bidPx": "99.9", "askPx": "100.1"}},
    }
    append_jsonl(
        aapl_path,
        {
            **base_row,
            "sequence": 1,
            "recv_ts_ms": 1700000000000,
            "source_ts_ms": 1700000000000,
            "canonical_symbol": "AAPL",
            "payload_sha256": "sha256:aapl",
        },
    )
    append_jsonl(
        sp500_path,
        {
            **base_row,
            "sequence": 1,
            "recv_ts_ms": 1700000121000,
            "source_ts_ms": 1700000121000,
            "canonical_symbol": "SP500",
            "payload_sha256": "sha256:sp500",
        },
    )
    manifest = build_trade_xyz_ws_quality_manifest(
        data_dir=data_dir, raw_ws_root=data_dir / "raw/ws/trade_xyz"
    )
    assert manifest["status"] == "pass"
    assert manifest["gap_count"] == 0
    assert manifest["source_ts_gap_count"] == 0


def test_build_trade_xyz_ws_quality_manifest_keeps_trade_gaps_informational(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    row_path = (
        data_dir
        / "raw/ws/trade_xyz/date=2026-06-01/subscription=trades/symbol=AAPL/part-000001.jsonl"
    )
    base_row = {
        "schema_version": "trade_xyz_ws_raw.v1",
        "source": "hyperliquid_ws",
        "source_tier": "official_ws",
        "dex": "xyz",
        "ws_url": "wss://api.hyperliquid.xyz/ws",
        "channel": "trades",
        "message_kind": "data",
        "subscription": "trades",
        "subscription_hash": "sha256:a",
        "connection_id": "c1",
        "recv_monotonic_ns": 1,
        "canonical_symbol": "AAPL",
        "payload": {"channel": "trades", "data": [{"coin": "xyz:AAPL", "time": 1700000000000}]},
    }
    append_jsonl(
        row_path,
        {
            **base_row,
            "sequence": 1,
            "recv_ts_ms": 1700000000000,
            "source_ts_ms": 1700000000000,
            "payload_sha256": "sha256:t1",
        },
    )
    append_jsonl(
        row_path,
        {
            **base_row,
            "sequence": 2,
            "recv_ts_ms": 1700000121000,
            "source_ts_ms": 1700000121000,
            "payload_sha256": "sha256:t2",
        },
    )
    manifest = build_trade_xyz_ws_quality_manifest(
        data_dir=data_dir, raw_ws_root=data_dir / "raw/ws/trade_xyz"
    )
    assert manifest["status"] == "pass"
    assert manifest["gap_count"] == 0
    assert manifest["source_ts_gap_count"] == 0
    assert manifest["trade_gap_count"] == 1
    assert manifest["trade_source_ts_gap_count"] == 1


def test_build_trade_xyz_ws_quality_manifest_keeps_duplicate_payloads_informational(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    raw_root = (
        data_dir / "raw/ws/trade_xyz/date=2026-06-01/subscription=activeAssetCtx/symbol=SP500"
    )
    row_path = raw_root / "part-000001.jsonl"
    base_row = {
        "schema_version": "trade_xyz_ws_raw.v1",
        "source": "hyperliquid_ws",
        "source_tier": "official_ws",
        "dex": "xyz",
        "ws_url": "wss://api.hyperliquid.xyz/ws",
        "channel": "activeAssetCtx",
        "message_kind": "data",
        "subscription": "activeAssetCtx",
        "subscription_hash": "sha256:a",
        "connection_id": "c1",
        "recv_monotonic_ns": 1,
        "canonical_symbol": "SP500",
        "payload_sha256": "sha256:duplicate",
        "payload": {
            "channel": "activeAssetCtx",
            "data": {"coin": "xyz:SP500", "ctx": {"markPx": "100.0"}},
        },
    }
    append_jsonl(row_path, {**base_row, "sequence": 1, "recv_ts_ms": 1700000000000})
    append_jsonl(row_path, {**base_row, "sequence": 2, "recv_ts_ms": 1700000001000})
    manifest = build_trade_xyz_ws_quality_manifest(
        data_dir=data_dir, raw_ws_root=data_dir / "raw/ws/trade_xyz"
    )
    assert manifest["duplicate_payload_count"] == 1
    assert manifest["status"] == "pass"
