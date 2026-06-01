from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from sis.venues.trade_xyz.ws_envelope import build_ws_raw_row


def test_ws_raw_row_matches_schema() -> None:
    schema = json.loads(Path("schemas/trade_xyz_ws_raw.v1.schema.json").read_text(encoding="utf-8"))
    row = build_ws_raw_row(
        ws_url="wss://api.hyperliquid.xyz/ws",
        dex="xyz",
        subscription="trades",
        requested_symbol="SP500",
        requested_coin="xyz:SP500",
        connection_id="conn-1",
        sequence=1,
        recv_ts_ms=1700000010000,
        recv_monotonic_ns=111,
        payload={"channel": "trades", "data": {"coin": "xyz:SP500", "time": 1700000000000}},
    )
    validate(instance=row, schema=schema)
