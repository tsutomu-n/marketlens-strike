from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sis.cli import app

from sis.crypto_perp.real_market_candle_validation import (
    CANDLE_AVAILABLE_BEFORE_BUCKET_CLOSE,
    CANDLE_OHLC_INVALID,
    CANDLE_TIMESTAMPS_NOT_UNIQUE,
    CANDLE_VOLUME_INVALID,
    LOOKBACK_CANDLES_NOT_CONTIGUOUS,
    validate_candle_rows,
    validate_signal_lookback_window,
)


def _row(ts: str, available_at: str) -> dict[str, str]:
    return {
        "ts": ts,
        "available_at": available_at,
        "open": "100",
        "high": "101",
        "low": "99",
        "close": "100",
        "quote_vol": "1",
    }


def test_rejects_full_candle_available_before_bucket_close() -> None:
    rows = [_row("2026-07-09T00:00:00Z", "2026-07-09T00:00:00Z")]

    with pytest.raises(ValueError, match=CANDLE_AVAILABLE_BEFORE_BUCKET_CLOSE):
        validate_candle_rows(rows, 5)


def test_rejects_duplicate_candle_timestamps() -> None:
    rows = [
        _row("2026-07-09T00:00:00Z", "2026-07-09T00:05:00Z"),
        _row("2026-07-09T00:00:00Z", "2026-07-09T00:05:00Z"),
    ]

    with pytest.raises(ValueError, match=CANDLE_TIMESTAMPS_NOT_UNIQUE):
        validate_candle_rows(rows, 5)


def test_rejects_gap_inside_signal_lookback_window() -> None:
    rows = [
        _row("2026-07-09T00:00:00Z", "2026-07-09T00:05:00Z"),
        _row("2026-07-09T00:10:00Z", "2026-07-09T00:15:00Z"),
        _row("2026-07-09T00:15:00Z", "2026-07-09T00:20:00Z"),
    ]

    with pytest.raises(ValueError, match=LOOKBACK_CANDLES_NOT_CONTIGUOUS):
        validate_signal_lookback_window(rows, 2, 3, 5)


runner = CliRunner()


def _write_csv(path: Path, *, early_available: bool = False, duplicate: bool = False) -> Path:
    base = datetime(2026, 7, 9, tzinfo=timezone.utc)
    lines = ["ts,available_at,symbol,open,high,low,close,base_vol,quote_vol"]
    for index in range(12):
        timestamp = base + timedelta(minutes=5 * index)
        if duplicate and index == 1:
            timestamp = base
        available_at = timestamp + timedelta(minutes=5)
        if early_available and index == 0:
            available_at = timestamp
        lines.append(
            f"{timestamp:%Y-%m-%dT%H:%M:%SZ},{available_at:%Y-%m-%dT%H:%M:%SZ},"
            "BTCUSDT,100,101,99,100,10,1000"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"early_available": True}, CANDLE_AVAILABLE_BEFORE_BUCKET_CLOSE),
        ({"duplicate": True}, CANDLE_TIMESTAMPS_NOT_UNIQUE),
    ],
)
def test_public_input_csv_rejects_invalid_candle_timing(
    tmp_path: Path, kwargs: dict[str, bool], expected: str
) -> None:
    input_csv = _write_csv(tmp_path / "candles.csv", **kwargs)

    result = runner.invoke(
        app,
        [
            "crypto-perp-real-market-no-cash-sample",
            "--input-csv",
            str(input_csv),
            "--out",
            str(tmp_path / "out"),
            "--target-event-count",
            "1",
            "--lookback-minutes",
            "5",
            "--horizon-minutes",
            "10",
            "--interval-minutes",
            "5",
        ],
    )

    assert result.exit_code == 2
    assert expected in result.stdout


@pytest.mark.parametrize(
    "option,value",
    [("--lookback-minutes", "64"), ("--horizon-minutes", "64")],
)
def test_public_sample_rejects_fractional_bar_windows(
    tmp_path: Path, option: str, value: str
) -> None:
    input_csv = _write_csv(tmp_path / "candles.csv")

    result = runner.invoke(
        app,
        [
            "crypto-perp-real-market-no-cash-sample",
            "--input-csv",
            str(input_csv),
            "--out",
            str(tmp_path / "out"),
            "--target-event-count",
            "1",
            option,
            value,
        ],
    )

    assert result.exit_code == 2
    assert "must be evenly divisible by interval_minutes" in result.stdout


def test_rejects_candle_whose_high_does_not_contain_close() -> None:
    row = _row("2026-07-09T00:00:00Z", "2026-07-09T00:05:00Z")
    row.update({"open": "100", "high": "100", "low": "99", "close": "101", "quote_vol": "1"})

    with pytest.raises(ValueError, match=CANDLE_OHLC_INVALID):
        validate_candle_rows([row], 5)


def test_rejects_negative_candle_volume() -> None:
    row = _row("2026-07-09T00:00:00Z", "2026-07-09T00:05:00Z")
    row.update({"open": "100", "high": "101", "low": "99", "close": "100", "quote_vol": "-1"})

    with pytest.raises(ValueError, match=CANDLE_VOLUME_INVALID):
        validate_candle_rows([row], 5)
