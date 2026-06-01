from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

SUPPORTED_WS_SUBSCRIPTIONS = {"bbo", "trades", "activeAssetCtx", "l2Book", "allMids"}


def stable_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_source_timestamp(payload: dict[str, Any]) -> tuple[int | None, str | None]:
    candidates = ("time", "t", "T")
    data = payload.get("data")
    if isinstance(data, dict):
        for key in candidates:
            value = data.get(key)
            if isinstance(value, int):
                return value, key
    for key in candidates:
        value = payload.get(key)
        if isinstance(value, int):
            return value, key
    return None, None


def classify_ws_message(payload: dict[str, Any]) -> tuple[str, str]:
    channel = payload.get("channel")
    if isinstance(channel, str):
        if channel in SUPPORTED_WS_SUBSCRIPTIONS:
            return channel, "data"
        if channel == "subscriptionResponse":
            return channel, "subscription_response"
        if channel == "pong":
            return channel, "heartbeat"
    return "__unknown__", "error"


def resolve_symbol_fields(
    *,
    message_kind: str,
    channel: str,
    payload: dict[str, Any],
    requested_symbol: str | None,
    requested_coin: str | None,
) -> tuple[str | None, str | None, str | None]:
    if message_kind != "data" or channel == "allMids":
        return None, None, None
    canonical_symbol = requested_symbol
    coin = requested_coin
    venue_symbol = requested_coin
    data = payload.get("data")
    if isinstance(data, dict):
        if coin is None and isinstance(data.get("coin"), str):
            coin = str(data.get("coin"))
            venue_symbol = coin
        if canonical_symbol is None and isinstance(data.get("coin"), str):
            canonical_symbol = str(data["coin"]).removeprefix("xyz:").upper()
    if canonical_symbol is None and coin is not None:
        canonical_symbol = coin.removeprefix("xyz:").upper()
    return canonical_symbol, venue_symbol, coin


def build_ws_raw_row(
    *,
    ws_url: str,
    dex: str,
    subscription: str,
    requested_symbol: str | None,
    requested_coin: str | None,
    connection_id: str,
    sequence: int,
    recv_ts_ms: int,
    recv_monotonic_ns: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    channel, message_kind = classify_ws_message(payload)
    source_ts_ms, source_ts_field = resolve_source_timestamp(payload)
    canonical_symbol, venue_symbol, coin = resolve_symbol_fields(
        message_kind=message_kind,
        channel=channel,
        payload=payload,
        requested_symbol=requested_symbol,
        requested_coin=requested_coin,
    )
    row: dict[str, Any] = {
        "schema_version": "trade_xyz_ws_raw.v1",
        "source": "hyperliquid_ws",
        "source_tier": "official_ws",
        "dex": dex,
        "ws_url": ws_url,
        "channel": channel,
        "message_kind": message_kind,
        "subscription": subscription,
        "subscription_hash": stable_sha256({"subscription": subscription, "coin": requested_coin}),
        "connection_id": connection_id,
        "sequence": sequence,
        "recv_ts_ms": recv_ts_ms,
        "recv_monotonic_ns": recv_monotonic_ns,
        "is_snapshot": False,
        "payload_sha256": stable_sha256(payload),
        "payload": payload,
    }
    if source_ts_ms is not None and source_ts_field is not None:
        row["source_ts_ms"] = source_ts_ms
        row["source_ts_field"] = source_ts_field
    if canonical_symbol is not None:
        row["canonical_symbol"] = canonical_symbol
    if venue_symbol is not None:
        row["venue_symbol"] = venue_symbol
    if coin is not None:
        row["coin"] = coin
    return row


def now_ts_ms() -> int:
    return int(datetime.now(tz=UTC).timestamp() * 1000)
