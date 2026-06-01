from __future__ import annotations

from pathlib import Path
import json

from jsonschema import validate
from sis.storage.jsonl_store import read_jsonl
from sis.venues.trade_xyz.ws_recorder import run_trade_xyz_ws_capture
from sis.venues.trade_xyz.ws_recorder import WsCaptureConfig
from sis.venues.trade_xyz.ws_recorder import WsSubscriptionTarget


async def _fake_source(**_kwargs):
    yield {"channel": "subscriptionResponse", "data": {"ok": True}}
    yield {"channel": "pong", "data": {"t": 1700000000000}}
    yield {
        "channel": "bbo",
        "data": {"coin": "xyz:SP500", "time": 1700000000123, "bidPx": "99.9", "askPx": "100.1"},
    }


def test_run_trade_xyz_ws_capture_writes_rows(tmp_path: Path) -> None:
    output_root = tmp_path / "data/raw/ws/trade_xyz"
    config = WsCaptureConfig(
        ws_url="wss://api.hyperliquid.xyz/ws",
        dex="xyz",
        output_root=output_root,
        duration_seconds=10,
        heartbeat_seconds=1,
        reconnect_max_attempts=2,
        reconnect_initial_delay_seconds=0.01,
        reconnect_max_delay_seconds=0.02,
        write_control_messages=True,
        dry_run=False,
    )
    targets = [WsSubscriptionTarget(subscription="bbo", canonical_symbol="SP500", coin="xyz:SP500")]
    manifest = run_trade_xyz_ws_capture(
        config=config,
        targets=targets,
        message_source_factory=_fake_source,
        recv_clock=lambda: (1700000010000, 123456789),
    )
    assert manifest["row_count"] == 3
    assert manifest["subscription_response_count"] == 1
    assert manifest["pong_count"] == 1
    files = sorted(output_root.rglob("*.jsonl"))
    assert files
    rows = []
    for file in files:
        rows.extend(list(read_jsonl(file)))
    assert rows
    assert any(row.get("message_kind") == "subscription_response" for row in rows)
    assert any(row.get("message_kind") == "heartbeat" for row in rows)
    assert any(row.get("message_kind") == "data" for row in rows)
    schema = json.loads(
        Path("schemas/trade_xyz_ws_capture_manifest.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=manifest, schema=schema)


def test_run_trade_xyz_ws_capture_dry_run(tmp_path: Path) -> None:
    config = WsCaptureConfig(
        ws_url="wss://api.hyperliquid.xyz/ws",
        dex="xyz",
        output_root=tmp_path / "raw/ws/trade_xyz",
        duration_seconds=10,
        heartbeat_seconds=1,
        reconnect_max_attempts=2,
        reconnect_initial_delay_seconds=0.01,
        reconnect_max_delay_seconds=0.02,
        write_control_messages=True,
        dry_run=True,
    )
    manifest = run_trade_xyz_ws_capture(
        config=config,
        targets=[WsSubscriptionTarget(subscription="allMids")],
    )
    assert manifest["dry_run"] is True
    assert manifest["row_count"] == 0
