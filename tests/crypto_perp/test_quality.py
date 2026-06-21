from __future__ import annotations

from sis.crypto_perp.bars import build_candle_bars, interval_to_milliseconds
from sis.crypto_perp.quality import validate_candle_series


def _bars(offsets: list[int], *, now_ms: int | None = None, high: str = "110"):
    base_ms = 1710000000000
    interval_ms = interval_to_milliseconds("15m")
    return build_candle_bars(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        candle_rows=[
            {
                "ts_open": str(base_ms + offset * interval_ms),
                "open": "100",
                "high": high,
                "low": "90",
                "close": "105",
                "base_volume": "10",
                "quote_turnover": "1000",
                "candle_type": "market",
                "interval": "15m",
            }
            for offset in offsets
        ],
        ts_ingested="2026-06-21T04:00:00Z",
        source_payload_sha256="b" * 64,
        now_ms=now_ms if now_ms is not None else base_ms + (max(offsets) + 2) * interval_ms,
    )


def test_gap_blocks_event_generation() -> None:
    report = validate_candle_series(_bars([0, 2]), interval="15m")

    assert report.gap_count == 1
    assert report.event_generation_allowed is False
    assert "GAP_DETECTED" in report.reason_codes


def test_non_final_bar_blocks_event_generation() -> None:
    base_ms = 1710000000000
    interval_ms = interval_to_milliseconds("15m")
    report = validate_candle_series(
        _bars([0, 1], now_ms=base_ms + interval_ms + 60_000),
        interval="15m",
    )

    assert report.non_final_count == 1
    assert report.event_generation_allowed is False
    assert "NON_FINAL_BAR" in report.reason_codes


def test_invalid_ohlc_blocks_event_generation() -> None:
    report = validate_candle_series(_bars([0], high="99"), interval="15m")

    assert report.ohlc_error_count == 1
    assert report.event_generation_allowed is False
    assert "INVALID_OHLC" in report.reason_codes
