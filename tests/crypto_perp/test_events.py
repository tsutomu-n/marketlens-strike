from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.bars import build_candle_bars, interval_to_milliseconds
from sis.crypto_perp.features import EventDetectorConfig
from sis.crypto_perp.events import detect_event
from sis.crypto_perp.quality import validate_candle_series
from .test_features import make_bars, ticker


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _write_csv(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "ts,available_at,symbol,open,high,low,close,base_vol,quote_vol",
                "2026-06-27T00:00:00Z,2026-06-27T00:00:00Z,BTCUSDT,100,101,99,100,1,100",
                "2026-06-27T00:05:00Z,2026-06-27T00:05:00Z,BTCUSDT,100,102,99,101,1,101",
                "2026-06-27T00:10:00Z,2026-06-27T00:10:00Z,BTCUSDT,101,103,100,102,1,102",
                "2026-06-27T00:15:00Z,2026-06-27T00:15:00Z,BTCUSDT,102,104,101,103,1,103",
                "2026-06-27T00:20:00Z,2026-06-27T00:20:00Z,BTCUSDT,103,105,102,104,1,104",
                "2026-06-27T00:25:00Z,2026-06-27T00:25:00Z,BTCUSDT,104,106,103,105,1,105",
                "2026-06-27T00:30:00Z,2026-06-27T00:30:00Z,BTCUSDT,105,107,104,106,1,106",
                "2026-06-27T00:35:00Z,2026-06-27T00:35:00Z,BTCUSDT,106,108,105,107,1,107",
                "2026-06-27T00:40:00Z,2026-06-27T00:40:00Z,BTCUSDT,107,109,106,108,1,108",
                "2026-06-27T00:45:00Z,2026-06-27T00:45:00Z,BTCUSDT,108,110,107,109,1,109",
                "2026-06-27T00:50:00Z,2026-06-27T00:50:00Z,BTCUSDT,109,111,108,110,1,110",
                "2026-06-27T00:55:00Z,2026-06-27T00:55:00Z,BTCUSDT,110,112,109,111,1,111",
                "2026-06-27T01:00:00Z,2026-06-27T01:00:00Z,BTCUSDT,111,113,110,112,1,112",
                "2026-06-27T01:05:00Z,2026-06-27T01:05:00Z,BTCUSDT,112,200,112,199,1,199",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_detect_event_emits_slow_fast_and_near_miss_families_without_direction_fields() -> None:
    config = EventDetectorConfig()
    near_closes = ["100"] * 296 + [
        str(100 + Decimal("3.5") * Decimal(index + 1) / Decimal("296")) for index in range(296)
    ]
    slow = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296),
        ticker=ticker(),
        quality_report=validate_candle_series(
            make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296),
            interval="15m",
        ),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=config,
    )
    fast = detect_event(
        provider_id="bitget",
        native_symbol="ETHUSDT",
        canonical_symbol="ETHUSDT",
        bars=make_bars(["100"] * 36 + ["101", "102", "103", "104"], ["1000"] * 36 + ["5000"] * 4),
        ticker=ticker().model_copy(update={"native_symbol": "ETHUSDT"}),
        quality_report=validate_candle_series(
            make_bars(
                ["100"] * 36 + ["101", "102", "103", "104"],
                ["1000"] * 36 + ["5000"] * 4,
            ),
            interval="15m",
        ),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=config,
    )
    near_miss = detect_event(
        provider_id="bitget",
        native_symbol="SOLUSDT",
        canonical_symbol="SOLUSDT",
        bars=make_bars(near_closes, ["1000"] * 296 + ["1130"] * 296),
        ticker=ticker().model_copy(update={"native_symbol": "SOLUSDT"}),
        quality_report=validate_candle_series(
            make_bars(near_closes, ["1000"] * 296 + ["1130"] * 296),
            interval="15m",
        ),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=config,
    )

    assert slow is not None and slow.event_family == "slow_pump_74h_v1"
    assert fast is not None and fast.event_family == "fast_pump_1h_v1"
    assert near_miss is not None and near_miss.event_family == "near_miss_v1"
    payload = slow.model_dump(mode="json")
    assert "action" not in payload
    assert "side" not in payload
    assert payload["status"] == "CAPTURE_REQUESTED"


def test_crypto_perp_event_record_cli_writes_market_window_without_future_rows(
    tmp_path: Path,
) -> None:
    csv_path = _write_csv(tmp_path / "BTCUSDT_5m_input.csv")
    out_dir = tmp_path / "events"

    result = runner.invoke(
        app,
        [
            "crypto-perp-event-record",
            "--input-csv",
            str(csv_path),
            "--symbol",
            "BTCUSDT",
            "--information-cutoff-at",
            "2026-06-27T01:00:00Z",
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    event_path_line = next(
        line for line in result.stdout.splitlines() if line.startswith("event_path=")
    )
    event_path = Path(event_path_line.split("=", 1)[1])
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crypto_perp_event.v1"
    assert payload["event_family"] == "market_window_v1"
    assert payload["information_cutoff_at"] == "2026-06-27T01:00:00Z"
    assert payload["features_at_detection"]["return_60m"] == "0.12"
    assert payload["features_at_detection"]["return_15m"] == "0.02752293577981651376146789"
    assert payload["features_at_detection"]["return_74h"] == "0"
    assert payload["boundary"]["permits_live_order"] is False
    assert payload["source_refs"][0]["path"] == csv_path.as_posix()


def test_event_dump_matches_schema() -> None:
    event = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296),
        ticker=ticker(),
        quality_report=validate_candle_series(
            make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296),
            interval="15m",
        ),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=EventDetectorConfig(),
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_event.v1.schema.json").read_text(encoding="utf-8")
    )

    assert event is not None
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(event.model_dump(mode="json"))


def test_event_features_are_cutoff_immutable_when_future_bars_are_added() -> None:
    bars = make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296)
    cutoff = bars[-1].ts_available
    event = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=bars,
        ticker=ticker(),
        quality_report=validate_candle_series(bars, interval="15m"),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=EventDetectorConfig(),
        information_cutoff_at=cutoff,
    )
    future_bars = bars + build_candle_bars(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        candle_rows=[
            {
                "ts_open": str(1710000000000 + len(bars) * interval_to_milliseconds("15m")),
                "open": "105",
                "high": "151",
                "low": "104",
                "close": "150",
                "base_volume": "10",
                "quote_turnover": "999999",
                "candle_type": "market",
                "interval": "15m",
            }
        ],
        ts_ingested="2026-06-21T04:00:00Z",
        source_payload_sha256="e" * 64,
        now_ms=1710000000000 + (len(bars) + 2) * interval_to_milliseconds("15m"),
    )
    event_with_future = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=future_bars,
        ticker=ticker(),
        quality_report=validate_candle_series(bars, interval="15m"),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=EventDetectorConfig(),
        information_cutoff_at=cutoff,
    )

    assert event is not None
    assert event_with_future is not None
    assert event.event_id == event_with_future.event_id
    assert event.features_at_detection == event_with_future.features_at_detection
