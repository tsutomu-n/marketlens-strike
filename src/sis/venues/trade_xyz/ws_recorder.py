from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from typing import Any, AsyncIterator, Callable

from sis.storage.jsonl_store import append_jsonl
from sis.venues.trade_xyz.ws_envelope import build_ws_raw_row
from sis.venues.trade_xyz.ws_envelope import SUPPORTED_WS_SUBSCRIPTIONS

WS_CONTROL_SUBSCRIPTION = "__control__"
WS_CONTROL_SYMBOL = "__all__"


@dataclass(frozen=True)
class WsSubscriptionTarget:
    subscription: str
    canonical_symbol: str | None = None
    coin: str | None = None


@dataclass(frozen=True)
class WsCaptureConfig:
    ws_url: str
    dex: str
    output_root: Path
    duration_seconds: int
    heartbeat_seconds: int
    reconnect_max_attempts: int
    reconnect_initial_delay_seconds: float
    reconnect_max_delay_seconds: float
    write_control_messages: bool
    dry_run: bool


def _row_path(output_root: Path, row: dict[str, Any]) -> Path:
    recv_ts_ms = int(row["recv_ts_ms"])
    dt = datetime.fromtimestamp(recv_ts_ms / 1000, tz=UTC)
    day = dt.date().isoformat()
    subscription = str(row["subscription"])
    symbol = str(row.get("canonical_symbol") or WS_CONTROL_SYMBOL)
    return (
        output_root
        / f"date={day}"
        / f"subscription={subscription}"
        / f"symbol={symbol}"
        / "part-000001.jsonl"
    )


def _subscription_request(target: WsSubscriptionTarget) -> dict[str, Any]:
    if target.subscription not in SUPPORTED_WS_SUBSCRIPTIONS:
        raise ValueError(f"unsupported ws subscription: {target.subscription}")
    subscription: dict[str, Any] = {"type": target.subscription}
    if target.coin is not None:
        subscription["coin"] = target.coin
    return {"method": "subscribe", "subscription": subscription}


async def _default_message_source_factory(
    *,
    ws_url: str,
    targets: list[WsSubscriptionTarget],
    heartbeat_seconds: int,
) -> AsyncIterator[dict[str, Any]]:
    import websockets

    async with websockets.connect(ws_url) as conn:
        for target in targets:
            await conn.send(json.dumps(_subscription_request(target), separators=(",", ":")))
        while True:
            try:
                raw = await asyncio.wait_for(conn.recv(), timeout=float(heartbeat_seconds))
            except asyncio.TimeoutError:
                await conn.ping()
                yield {"channel": "pong", "data": {"clientHeartbeat": True}}
                continue
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                yield parsed
            else:
                yield {"channel": "__unknown__", "data": {"raw": parsed}}


async def capture_trade_xyz_ws(
    *,
    config: WsCaptureConfig,
    targets: list[WsSubscriptionTarget],
    message_source_factory: Callable[..., AsyncIterator[dict[str, Any]]] | None = None,
    recv_clock: Callable[[], tuple[int, int]] | None = None,
) -> dict[str, Any]:
    if config.duration_seconds <= 0:
        raise ValueError("duration_seconds must be > 0")
    if config.heartbeat_seconds <= 0:
        raise ValueError("heartbeat_seconds must be > 0")
    if config.reconnect_max_attempts <= 0:
        raise ValueError("reconnect_max_attempts must be > 0")
    source_factory = message_source_factory or _default_message_source_factory
    clock = recv_clock or (lambda: (int(time.time() * 1000), time.monotonic_ns()))
    started = datetime.now(tz=UTC)
    deadline = time.monotonic() + config.duration_seconds
    raw_paths: set[str] = set()
    row_count = 0
    bytes_written = 0
    connection_count = 0
    reconnect_count = 0
    error_count = 0
    subscription_response_count = 0
    pong_count = 0
    heartbeat_sent_count = 0
    block_reasons: list[str] = []
    if config.dry_run:
        ended = datetime.now(tz=UTC)
        manifest = {
            "schema_version": "trade_xyz_ws_capture_manifest.v1",
            "source": "hyperliquid_ws",
            "dex": config.dex,
            "started_at": started.isoformat(),
            "ended_at": ended.isoformat(),
            "duration_seconds": max(0.0, (ended - started).total_seconds()),
            "subscriptions": [target.subscription for target in targets],
            "symbols": [target.canonical_symbol for target in targets if target.canonical_symbol],
            "raw_paths": [],
            "row_count": 0,
            "bytes_written": 0,
            "connection_count": 0,
            "reconnect_count": 0,
            "error_count": 0,
            "subscription_response_count": 0,
            "pong_count": 0,
            "heartbeat_sent_count": 0,
            "dry_run": True,
            "block_reasons": [],
        }
        return manifest

    delay = config.reconnect_initial_delay_seconds
    connection_index = 0
    while time.monotonic() < deadline:
        connection_index += 1
        connection_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{connection_index:04d}"
        connection_count += 1
        seq = 0
        try:
            async for payload in source_factory(
                ws_url=config.ws_url,
                targets=targets,
                heartbeat_seconds=config.heartbeat_seconds,
            ):
                now_mono = time.monotonic()
                if now_mono >= deadline:
                    break
                seq += 1
                recv_ts_ms, recv_monotonic_ns = clock()
                channel = payload.get("channel")
                row_subscription = (
                    WS_CONTROL_SUBSCRIPTION
                    if channel in {"subscriptionResponse", "pong"}
                    else str(channel or "__unknown__")
                )
                row = build_ws_raw_row(
                    ws_url=config.ws_url,
                    dex=config.dex,
                    subscription=row_subscription,
                    requested_symbol=None,
                    requested_coin=None,
                    connection_id=connection_id,
                    sequence=seq,
                    recv_ts_ms=recv_ts_ms,
                    recv_monotonic_ns=recv_monotonic_ns,
                    payload=payload,
                )
                if row["message_kind"] == "subscription_response":
                    subscription_response_count += 1
                    row["subscription"] = WS_CONTROL_SUBSCRIPTION
                elif row["message_kind"] == "heartbeat":
                    pong_count += 1
                    row["subscription"] = WS_CONTROL_SUBSCRIPTION
                elif row["message_kind"] == "error":
                    error_count += 1
                    row["subscription"] = WS_CONTROL_SUBSCRIPTION
                if row["message_kind"] in {"subscription_response", "heartbeat", "error"}:
                    row.pop("canonical_symbol", None)
                    row.pop("venue_symbol", None)
                    row.pop("coin", None)
                if (
                    not config.write_control_messages
                    and row["subscription"] == WS_CONTROL_SUBSCRIPTION
                ):
                    continue
                path = _row_path(config.output_root, row)
                append_jsonl(path, row)
                raw_paths.add(str(path))
                row_count += 1
                bytes_written += len(json.dumps(row, ensure_ascii=False, default=str)) + 1
                if row["message_kind"] == "heartbeat":
                    heartbeat_sent_count += 1
        except Exception as exc:  # pragma: no cover - exercised via tests with fake source
            reconnect_count += 1
            error_count += 1
            block_reasons.append(str(exc))
            if reconnect_count >= config.reconnect_max_attempts:
                break
            await asyncio.sleep(min(delay, config.reconnect_max_delay_seconds))
            delay = min(delay * 2, config.reconnect_max_delay_seconds)
            continue
        break

    ended = datetime.now(tz=UTC)
    manifest = {
        "schema_version": "trade_xyz_ws_capture_manifest.v1",
        "source": "hyperliquid_ws",
        "dex": config.dex,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_seconds": max(0.0, (ended - started).total_seconds()),
        "subscriptions": [target.subscription for target in targets],
        "symbols": [target.canonical_symbol for target in targets if target.canonical_symbol],
        "raw_paths": sorted(raw_paths),
        "row_count": row_count,
        "bytes_written": bytes_written,
        "connection_count": connection_count,
        "reconnect_count": reconnect_count,
        "error_count": error_count,
        "subscription_response_count": subscription_response_count,
        "pong_count": pong_count,
        "heartbeat_sent_count": heartbeat_sent_count,
        "dry_run": False,
        "block_reasons": block_reasons,
    }
    return manifest


def run_trade_xyz_ws_capture(
    *,
    config: WsCaptureConfig,
    targets: list[WsSubscriptionTarget],
    message_source_factory: Callable[..., AsyncIterator[dict[str, Any]]] | None = None,
    recv_clock: Callable[[], tuple[int, int]] | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        capture_trade_xyz_ws(
            config=config,
            targets=targets,
            message_source_factory=message_source_factory,
            recv_clock=recv_clock,
        )
    )
