from __future__ import annotations

import json

from sis.crypto_perp.ws_protocol import (
    BitgetWsTarget,
    build_subscribe_message,
    parse_bitget_public_message,
)


def test_build_subscribe_message_maps_internal_channels_to_bitget_public_channels() -> None:
    payload = build_subscribe_message(
        [
            BitgetWsTarget(inst_type="USDT-FUTURES", channel="trades", inst_id="BTCUSDT"),
            BitgetWsTarget(inst_type="USDT-FUTURES", channel="books1", inst_id="BTCUSDT"),
            BitgetWsTarget(inst_type="USDT-FUTURES", channel="books15", inst_id="ETHUSDT"),
        ]
    )

    assert payload == {
        "op": "subscribe",
        "args": [
            {"instType": "USDT-FUTURES", "channel": "trade", "instId": "BTCUSDT"},
            {"instType": "USDT-FUTURES", "channel": "books1", "instId": "BTCUSDT"},
            {"instType": "USDT-FUTURES", "channel": "books15", "instId": "ETHUSDT"},
        ],
    }


def test_parse_bitget_public_trade_and_book_messages() -> None:
    trade = parse_bitget_public_message(
        json.dumps(
            {
                "arg": {"instType": "USDT-FUTURES", "channel": "trade", "instId": "BTCUSDT"},
                "data": [{"tradeId": "1", "price": "100", "size": "0.1", "side": "buy"}],
                "ts": 1710000000000,
            }
        )
    )
    book = parse_bitget_public_message(
        {
            "action": "snapshot",
            "arg": {"instType": "USDT-FUTURES", "channel": "books1", "instId": "BTCUSDT"},
            "data": [
                {
                    "asks": [["101", "2"]],
                    "bids": [["100", "1"]],
                    "checksum": 0,
                    "seq": 10,
                    "ts": "1710000000010",
                }
            ],
            "ts": 1710000000010,
        }
    )

    assert trade.kind == "data"
    assert trade.channel == "trades"
    assert trade.native_symbol == "BTCUSDT"
    assert trade.ts_event_ms == 1710000000000
    assert book.kind == "data"
    assert book.channel == "books1"
    assert book.action == "snapshot"
    assert book.data[0]["seq"] == 10


def test_parse_bitget_public_control_and_error_messages() -> None:
    subscription = parse_bitget_public_message(
        {"event": "subscribe", "arg": {"channel": "books1", "instId": "BTCUSDT"}}
    )
    error = parse_bitget_public_message({"event": "error", "code": "30001", "msg": "bad"})

    assert subscription.kind == "subscription"
    assert subscription.channel == "books1"
    assert error.kind == "error"
    assert error.error_code == "30001"
