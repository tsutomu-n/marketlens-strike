from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import json
from types import SimpleNamespace

from jsonschema import validate
from sis.storage.jsonl_store import read_jsonl
from sis.venues.trade_xyz.ws_recorder import _default_message_source_factory
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


async def _fake_source_without_coin(**_kwargs):
    yield {
        "channel": "bbo",
        "data": {"time": 1700000000123, "bidPx": "99.9", "askPx": "100.1"},
    }


async def _fake_trades_source_with_list_payload(**_kwargs):
    yield {
        "channel": "trades",
        "data": [
            {
                "coin": "xyz:NVDA",
                "side": "B",
                "px": "215.29",
                "sz": "6.193",
                "time": 1700000000123,
            }
        ],
    }


def _config(tmp_path: Path, *, reconnect_max_attempts: int = 2) -> WsCaptureConfig:
    return WsCaptureConfig(
        ws_url="wss://api.hyperliquid.xyz/ws",
        dex="xyz",
        output_root=tmp_path / "data/raw/ws/trade_xyz",
        duration_seconds=10,
        heartbeat_seconds=1,
        reconnect_max_attempts=reconnect_max_attempts,
        reconnect_initial_delay_seconds=0.01,
        reconnect_max_delay_seconds=0.02,
        write_control_messages=True,
        dry_run=False,
    )


def test_run_trade_xyz_ws_capture_writes_rows(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output_root = config.output_root
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
    assert manifest["heartbeat_sent_count"] == 0
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


def test_run_trade_xyz_ws_capture_keeps_expected_expiry_out_of_error_budget(
    tmp_path: Path,
) -> None:
    calls = 0

    async def source(**_kwargs):
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise RuntimeError("received 1000 (OK) Expired; then sent 1000 (OK) Expired")
        yield {"channel": "subscriptionResponse", "data": {"ok": True}}
        yield {
            "channel": "bbo",
            "data": {
                "coin": "xyz:SP500",
                "time": 1700000000123,
                "bidPx": "99.9",
                "askPx": "100.1",
            },
        }

    manifest = run_trade_xyz_ws_capture(
        config=_config(tmp_path, reconnect_max_attempts=1),
        targets=[
            WsSubscriptionTarget(subscription="bbo", canonical_symbol="SP500", coin="xyz:SP500")
        ],
        message_source_factory=source,
        recv_clock=lambda: (1700000010000, 123456789),
    )

    assert calls == 3
    assert manifest["row_count"] == 2
    assert manifest["reconnect_count"] == 2
    assert manifest["graceful_reconnect_count"] == 2
    assert manifest["unexpected_reconnect_count"] == 0
    assert manifest["error_count"] == 0


def test_run_trade_xyz_ws_capture_stops_at_unexpected_reconnect_budget(
    tmp_path: Path,
) -> None:
    calls = 0

    async def source(**_kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("sent 1011 (internal error) keepalive ping timeout")
        yield  # pragma: no cover

    manifest = run_trade_xyz_ws_capture(
        config=_config(tmp_path, reconnect_max_attempts=2),
        targets=[
            WsSubscriptionTarget(subscription="bbo", canonical_symbol="SP500", coin="xyz:SP500")
        ],
        message_source_factory=source,
        recv_clock=lambda: (1700000010000, 123456789),
    )

    assert calls == 2
    assert manifest["row_count"] == 0
    assert manifest["reconnect_count"] == 2
    assert manifest["graceful_reconnect_count"] == 0
    assert manifest["unexpected_reconnect_count"] == 2
    assert manifest["error_count"] == 2


def test_default_message_source_sends_application_ping_on_timeout(monkeypatch) -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.sent: list[dict[str, object]] = []
            self.recv_count = 0

        async def send(self, payload: str) -> None:
            self.sent.append(json.loads(payload))

        async def recv(self) -> str:
            self.recv_count += 1
            if self.recv_count == 1:
                raise asyncio.TimeoutError
            return json.dumps({"channel": "pong", "data": {"server": True}})

        async def ping(self) -> None:
            raise AssertionError("websocket protocol ping must not be used for heartbeat")

    class FakeConnect:
        def __init__(self, conn: FakeConnection) -> None:
            self.conn = conn

        async def __aenter__(self) -> FakeConnection:
            return self.conn

        async def __aexit__(self, *_args: object) -> None:
            return None

    conn = FakeConnection()
    monkeypatch.setitem(
        sys.modules,
        "websockets",
        SimpleNamespace(connect=lambda _url: FakeConnect(conn)),
    )
    heartbeat_sent_count = 0

    def record_heartbeat_sent() -> None:
        nonlocal heartbeat_sent_count
        heartbeat_sent_count += 1

    async def read_first_payload() -> dict[str, object]:
        source = _default_message_source_factory(
            ws_url="wss://api.hyperliquid.xyz/ws",
            targets=[
                WsSubscriptionTarget(
                    subscription="bbo",
                    canonical_symbol="SP500",
                    coin="xyz:SP500",
                )
            ],
            heartbeat_seconds=1,
            heartbeat_sent_callback=record_heartbeat_sent,
        )
        try:
            return await anext(source)
        finally:
            await source.aclose()

    payload = asyncio.run(read_first_payload())

    assert conn.sent == [
        {"method": "subscribe", "subscription": {"type": "bbo", "coin": "xyz:SP500"}},
        {"method": "ping"},
    ]
    assert payload == {"channel": "pong", "data": {"server": True}}
    assert heartbeat_sent_count == 1


def test_default_message_source_stops_after_deadline_without_extra_ping(monkeypatch) -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.sent: list[dict[str, object]] = []

        async def send(self, payload: str) -> None:
            self.sent.append(json.loads(payload))

        async def recv(self) -> str:
            raise AssertionError("recv must not be called after deadline")

    class FakeConnect:
        def __init__(self, conn: FakeConnection) -> None:
            self.conn = conn

        async def __aenter__(self) -> FakeConnection:
            return self.conn

        async def __aexit__(self, *_args: object) -> None:
            return None

    conn = FakeConnection()
    monkeypatch.setitem(
        sys.modules,
        "websockets",
        SimpleNamespace(connect=lambda _url: FakeConnect(conn)),
    )

    async def read_payload() -> None:
        source = _default_message_source_factory(
            ws_url="wss://api.hyperliquid.xyz/ws",
            targets=[
                WsSubscriptionTarget(
                    subscription="bbo",
                    canonical_symbol="SP500",
                    coin="xyz:SP500",
                )
            ],
            heartbeat_seconds=1,
            stop_time_monotonic=0.0,
        )
        try:
            await anext(source)
        finally:
            await source.aclose()

    try:
        asyncio.run(read_payload())
    except StopAsyncIteration:
        pass
    else:  # pragma: no cover
        raise AssertionError("source must stop after deadline")

    assert conn.sent == [
        {"method": "subscribe", "subscription": {"type": "bbo", "coin": "xyz:SP500"}}
    ]


def test_run_trade_xyz_ws_capture_uses_single_target_symbol_fallback(tmp_path: Path) -> None:
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
        message_source_factory=_fake_source_without_coin,
        recv_clock=lambda: (1700000010000, 123456789),
    )
    assert manifest["row_count"] == 1
    rows = []
    for file in sorted(output_root.rglob("*.jsonl")):
        rows.extend(list(read_jsonl(file)))
    assert rows[0]["canonical_symbol"] == "SP500"
    assert rows[0]["coin"] == "xyz:SP500"


def test_run_trade_xyz_ws_capture_resolves_trades_list_payload_symbol(tmp_path: Path) -> None:
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
    targets = [
        WsSubscriptionTarget(subscription="trades", canonical_symbol="SP500", coin="xyz:SP500"),
        WsSubscriptionTarget(subscription="trades", canonical_symbol="NVDA", coin="xyz:NVDA"),
    ]
    manifest = run_trade_xyz_ws_capture(
        config=config,
        targets=targets,
        message_source_factory=_fake_trades_source_with_list_payload,
        recv_clock=lambda: (1700000010000, 123456789),
    )
    assert manifest["row_count"] == 1
    files = sorted(output_root.rglob("*.jsonl"))
    assert [file.as_posix() for file in files] == [
        (
            output_root / "date=2023-11-14/subscription=trades/symbol=NVDA/part-000001.jsonl"
        ).as_posix()
    ]
    rows = []
    for file in files:
        rows.extend(list(read_jsonl(file)))
    assert rows[0]["canonical_symbol"] == "NVDA"
    assert rows[0]["coin"] == "xyz:NVDA"


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
