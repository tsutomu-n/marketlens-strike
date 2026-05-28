from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from sis.real_market.providers.alpaca import AlpacaProviderUnavailable, fetch_alpaca_bars
from sis.real_market.alpaca_smoke import run_alpaca_live_smoke


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


def test_alpaca_live_smoke_writes_failed_summary_without_credentials(
    tmp_path,
    monkeypatch,
) -> None:
    for key in (
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "SIS_ALPACA_API_KEY",
        "SIS_ALPACA_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    summary = run_alpaca_live_smoke(data_dir=tmp_path, symbol="NVDA", timeframe="15m")

    assert summary["status"] == "failed"
    assert summary["error_class"] == "AlpacaProviderUnavailable"
    assert "credentials" in str(summary["error_message"])
    summary_path = tmp_path / "ops/alpaca_live_smoke_summary.json"
    report_path = tmp_path / "reports/alpaca_live_smoke.md"
    assert summary_path.exists()
    assert report_path.exists()
    written = summary_path.read_text(encoding="utf-8")
    assert "APCA_API_SECRET_KEY" not in written
    assert "secret" not in written.lower()


def test_alpaca_live_smoke_passes_and_writes_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APCA_API_KEY_ID", "key")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")

    def opener(request, *, timeout: float):
        _ = (request, timeout)
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

    summary = run_alpaca_live_smoke(
        data_dir=tmp_path,
        symbol="NVDA",
        timeframe="15m",
        opener=opener,
        now=datetime(2026, 5, 26, 14, 16, tzinfo=timezone.utc),
    )

    assert summary["status"] == "pass"
    assert summary["bar_count"] == 1
    assert summary["provider"] == "alpaca"
    assert summary["latest_close"] == 100.5
    assert (tmp_path / "ops/alpaca_live_smoke_summary.json").exists()
    assert (tmp_path / "reports/alpaca_live_smoke.md").exists()
    assert (tmp_path / "raw/real_market/alpaca/NVDA_15m_latest.json").exists()


def test_alpaca_live_smoke_blocks_low_source_confidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APCA_API_KEY_ID", "key")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")

    def opener(request, *, timeout: float):
        _ = (request, timeout)
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

    summary = run_alpaca_live_smoke(
        data_dir=tmp_path,
        symbol="NVDA",
        timeframe="15m",
        opener=opener,
        now=datetime(2026, 5, 26, 14, 45, tzinfo=timezone.utc),
    )

    assert summary["status"] == "blocked"
    assert summary["error_class"] == "AlpacaLiveSuitabilityBlocked"
    assert summary["live_suitability_reasons"] == ["BLOCK_LOW_SOURCE_CONFIDENCE"]
    report = (tmp_path / "reports/alpaca_live_smoke.md").read_text(encoding="utf-8")
    assert "status: blocked" in report
    assert "BLOCK_LOW_SOURCE_CONFIDENCE" in report
