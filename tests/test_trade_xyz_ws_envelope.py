from __future__ import annotations

from sis.venues.trade_xyz.ws_envelope import build_ws_raw_row
from sis.venues.trade_xyz.ws_envelope import classify_ws_message
from sis.venues.trade_xyz.ws_envelope import stable_sha256


def test_stable_sha256_is_key_order_insensitive() -> None:
    a = {"x": 1, "y": {"b": 2, "a": 1}}
    b = {"y": {"a": 1, "b": 2}, "x": 1}
    assert stable_sha256(a) == stable_sha256(b)


def test_classify_ws_message() -> None:
    assert classify_ws_message({"channel": "bbo"}) == ("bbo", "data")
    assert classify_ws_message({"channel": "subscriptionResponse"}) == (
        "subscriptionResponse",
        "subscription_response",
    )
    assert classify_ws_message({"channel": "pong"}) == ("pong", "heartbeat")
    assert classify_ws_message({"foo": "bar"}) == ("__unknown__", "error")


def test_build_ws_raw_row_keeps_source_timestamp_separate() -> None:
    payload = {"channel": "bbo", "data": {"coin": "xyz:SP500", "time": 1700000000000}}
    row = build_ws_raw_row(
        ws_url="wss://api.hyperliquid.xyz/ws",
        dex="xyz",
        subscription="bbo",
        requested_symbol="SP500",
        requested_coin="xyz:SP500",
        connection_id="conn-1",
        sequence=1,
        recv_ts_ms=1700000010000,
        recv_monotonic_ns=123,
        payload=payload,
    )
    assert row["source_ts_ms"] == 1700000000000
    assert row["source_ts_field"] == "time"
    assert row["recv_ts_ms"] == 1700000010000
    assert "oracle_ts_ms" not in row
    assert row["canonical_symbol"] == "SP500"


def test_build_ws_raw_row_without_source_ts_does_not_fill_from_recv_ts() -> None:
    payload = {"channel": "activeAssetCtx", "data": {"coin": "xyz:SP500"}}
    row = build_ws_raw_row(
        ws_url="wss://api.hyperliquid.xyz/ws",
        dex="xyz",
        subscription="activeAssetCtx",
        requested_symbol="SP500",
        requested_coin="xyz:SP500",
        connection_id="conn-1",
        sequence=2,
        recv_ts_ms=1700000010000,
        recv_monotonic_ns=456,
        payload=payload,
    )
    assert "source_ts_ms" not in row
    assert row["recv_ts_ms"] == 1700000010000


def test_build_ws_raw_row_resolves_trades_list_symbol_and_source_time() -> None:
    payload = {
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
    row = build_ws_raw_row(
        ws_url="wss://api.hyperliquid.xyz/ws",
        dex="xyz",
        subscription="trades",
        requested_symbol="NVDA",
        requested_coin="xyz:NVDA",
        connection_id="conn-1",
        sequence=3,
        recv_ts_ms=1700000010000,
        recv_monotonic_ns=789,
        payload=payload,
    )
    assert row["source_ts_ms"] == 1700000000123
    assert row["source_ts_field"] == "data[].time"
    assert row["canonical_symbol"] == "NVDA"
    assert row["coin"] == "xyz:NVDA"
