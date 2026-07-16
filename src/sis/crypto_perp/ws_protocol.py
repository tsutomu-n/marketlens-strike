from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

InternalWsChannel = Literal["trades", "books", "books1", "books15"]
BitgetMessageKind = Literal["data", "subscription", "pong", "error", "unknown"]
BITGET_CHANNEL_BY_INTERNAL: dict[str, str] = {
    "trades": "trade",
    "books": "books",
    "books1": "books1",
    "books15": "books15",
}
INTERNAL_CHANNEL_BY_BITGET = {
    value: key for key, value in BITGET_CHANNEL_BY_INTERNAL.items()
}


class BitgetWsTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    inst_type: Literal["USDT-FUTURES"]
    channel: InternalWsChannel
    inst_id: str

    @field_validator("inst_id")
    @classmethod
    def validate_inst_id(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped or stripped == "*":
            raise ValueError("Bitget WS target must be a candidate symbol")
        return stripped


class ParsedBitgetWsMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: BitgetMessageKind
    inst_type: str | None = None
    channel: str | None = None
    native_symbol: str | None = None
    action: str | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    ts_event_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw: dict[str, Any]


def build_subscribe_message(targets: list[BitgetWsTarget]) -> dict[str, Any]:
    return {
        "op": "subscribe",
        "args": [
            {
                "instType": target.inst_type,
                "channel": BITGET_CHANNEL_BY_INTERNAL[target.channel],
                "instId": target.inst_id,
            }
            for target in targets
        ],
    }


def _payload(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped == "pong":
            return {"op": "pong"}
        if stripped == "ping":
            return {"op": "ping"}
        parsed = json.loads(stripped)
    else:
        parsed = raw
    if not isinstance(parsed, dict):
        raise ValueError("Bitget WS message must be a JSON object")
    return parsed


def _arg(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("arg")
    return value if isinstance(value, dict) else {}


def _data_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _millisecond_value(value: object) -> int | None:
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _ts_event_ms(payload: dict[str, Any], data: list[dict[str, Any]]) -> int | None:
    # Bitget depth/trade rows carry the match/fill timestamp inside data items.
    # The top-level ts is the stream publication timestamp and is only a fallback.
    if data:
        item_ts = _millisecond_value(data[0].get("ts"))
        if item_ts is not None:
            return item_ts
    return _millisecond_value(payload.get("ts"))


def parse_bitget_public_message(raw: str | dict[str, Any]) -> ParsedBitgetWsMessage:
    payload = _payload(raw)
    event = payload.get("event")
    arg = _arg(payload)
    raw_channel = arg.get("channel")
    channel = (
        INTERNAL_CHANNEL_BY_BITGET.get(str(raw_channel), str(raw_channel or ""))
        or None
    )
    if event in {"subscribe", "unsubscribe"}:
        return ParsedBitgetWsMessage(
            kind="subscription",
            inst_type=(
                str(arg.get("instType")) if arg.get("instType") is not None else None
            ),
            channel=channel,
            native_symbol=(
                str(arg.get("instId")) if arg.get("instId") is not None else None
            ),
            raw=payload,
        )
    if event == "pong" or payload.get("op") == "pong":
        return ParsedBitgetWsMessage(kind="pong", raw=payload)
    if event == "error":
        return ParsedBitgetWsMessage(
            kind="error",
            channel=channel,
            error_code=(
                str(payload.get("code")) if payload.get("code") is not None else None
            ),
            error_message=(
                str(payload.get("msg")) if payload.get("msg") is not None else None
            ),
            raw=payload,
        )
    data = _data_list(payload)
    if arg and data:
        return ParsedBitgetWsMessage(
            kind="data",
            inst_type=(
                str(arg.get("instType")) if arg.get("instType") is not None else None
            ),
            channel=channel,
            native_symbol=(
                str(arg.get("instId")) if arg.get("instId") is not None else None
            ),
            action=(
                str(payload.get("action")) if payload.get("action") is not None else None
            ),
            data=data,
            ts_event_ms=_ts_event_ms(payload, data),
            raw=payload,
        )
    return ParsedBitgetWsMessage(kind="unknown", raw=payload)
