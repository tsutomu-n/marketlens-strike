from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from sis.real_market.providers.alpaca import AlpacaProviderUnavailable, fetch_alpaca_bars


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_alpaca_provider_requires_credentials(monkeypatch) -> None:
    for key in (
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "SIS_ALPACA_API_KEY",
        "SIS_ALPACA_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(AlpacaProviderUnavailable, match="credentials"):
        fetch_alpaca_bars(symbol="NVDA", timeframe="15m")


def test_alpaca_provider_maps_bars_and_writes_raw_payload(tmp_path) -> None:
    captured = {}

    def opener(request, *, timeout: float):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return _Response(
            {
                "bars": {
                    "NVDA": [
                        {
                            "t": "2026-05-26T14:00:00Z",
                            "o": 100.0,
                            "h": 101.0,
                            "l": 99.5,
                            "c": 100.5,
                            "v": 12345,
                        }
                    ]
                }
            }
        )

    raw_path = tmp_path / "raw/alpaca/NVDA_15m.json"
    bars = fetch_alpaca_bars(
        symbol="NVDA",
        timeframe="15m",
        start=datetime(2026, 5, 26, 13, 45, tzinfo=timezone.utc),
        end=datetime(2026, 5, 26, 14, 15, tzinfo=timezone.utc),
        api_key="key",
        api_secret="secret",
        opener=opener,
        raw_payload_path=raw_path,
    )

    assert len(bars) == 1
    assert bars[0].symbol == "NVDA"
    assert bars[0].timeframe == "15m"
    assert bars[0].source == "alpaca"
    assert bars[0].close == 100.5
    assert bars[0].volume == 12345.0
    assert bars[0].raw_payload_ref == str(raw_path)
    assert "timeframe=15Min" in str(captured["url"])
    assert "symbols=NVDA" in str(captured["url"])
    assert raw_path.exists()
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    assert raw_payload["provider"] == "alpaca"
    assert raw_payload["row_count"] == 1


def test_alpaca_provider_does_not_silent_pass_empty_response() -> None:
    def opener(request, *, timeout: float):
        _ = (request, timeout)
        return _Response({"bars": {"NVDA": []}})

    with pytest.raises(AlpacaProviderUnavailable, match="returned no bars"):
        fetch_alpaca_bars(
            symbol="NVDA",
            timeframe="15m",
            api_key="key",
            api_secret="secret",
            opener=opener,
        )
