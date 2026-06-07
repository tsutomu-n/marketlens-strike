import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
from jsonschema import validate
from typer.testing import CliRunner

from sis.cli import app
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.candles import SIGNAL_CANDLE_SCHEMA
from sis.venues.trade_xyz.candles import collect_trade_xyz_signal_candles
from sis.venues.trade_xyz.candles import signal_candles_manifest_is_fresh


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "venue": "trade_xyz",
                    "canonical_symbol": "SP500",
                    "venue_symbol": "SP500",
                    "asset_class": "index",
                    "dex": "xyz",
                    "coin": "xyz:SP500",
                    "real_market_symbol": "SPY",
                    "active": True,
                }
            ]
        ),
        encoding="utf-8",
    )


class FakeCandleClient:
    def __init__(self) -> None:
        self.requests = []

    def candle_snapshot(self, coin: str, interval: str, start_ms: int, end_ms: int):
        self.requests.append((coin, interval, start_ms, end_ms))
        return [
            {
                "t": start_ms,
                "T": start_ms + 1_799_999,
                "s": coin,
                "i": interval,
                "o": "5200.0",
                "h": "5210.0",
                "l": "5190.0",
                "c": "5205.0",
                "v": "123.45",
                "n": 12,
            }
        ]

    def close(self):
        return None


class ControlledCandleClient(FakeCandleClient):
    def __init__(
        self,
        *,
        failures_before_success: dict[tuple[str, str], int] | None = None,
        empty_success_keys: set[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__()
        self.failures_before_success = failures_before_success or {}
        self.empty_success_keys = empty_success_keys or set()
        self.call_counts: dict[tuple[str, str], int] = {}

    def candle_snapshot(self, coin: str, interval: str, start_ms: int, end_ms: int):
        key = (coin, interval)
        self.call_counts[key] = self.call_counts.get(key, 0) + 1
        failure_count = self.failures_before_success.get(key, 0)
        if self.call_counts[key] <= failure_count:
            raise RuntimeError("TradeXyzApiError: info endpoint failed: 429 null")
        if key in self.empty_success_keys:
            self.requests.append((coin, interval, start_ms, end_ms))
            return []
        return super().candle_snapshot(coin, interval, start_ms, end_ms)


def test_collect_trade_xyz_signal_candles_writes_separate_signal_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    client = FakeCandleClient()

    manifest = collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m", "4h"],
        period_days=1,
        request_delay_seconds=0,
        client=client,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["row_count"] == 2
    assert manifest["symbol_count"] == 1
    assert manifest["symbols"] == ["SP500"]
    assert manifest["request_error_count"] == 0
    assert manifest["request_delay_seconds"] == 0
    assert manifest["intervals"] == ["30m", "4h"]
    assert len(client.requests) == 2
    assert (data_dir / "manifests/trade_xyz_signal_candles_manifest.json").exists()
    validate(manifest, read_json(Path("schemas/trade_xyz_signal_candles_manifest.v1.schema.json")))
    frame = pl.read_parquet(data_dir / "normalized/trade_xyz_signal_candles.parquet")
    assert frame.height == 2
    assert frame.get_column("canonical_symbol").to_list() == ["SP500", "SP500"]
    assert frame.get_column("source").to_list() == [
        "hyperliquid_info_candleSnapshot",
        "hyperliquid_info_candleSnapshot",
    ]
    assert "raw/quotes" not in manifest["artifacts"]["normalized_signal_candles"]


def test_collect_trade_xyz_signal_candles_cli_writes_manifest(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")

    class ContextCandleClient(FakeCandleClient):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("sis.commands.quotes.TradeXyzClient", ContextCandleClient)

    result = CliRunner().invoke(
        app,
        [
            "collect-trade-xyz-signal-candles",
            "--symbols",
            "SP500",
            "--intervals",
            "30m",
            "--period-days",
            "1",
            "--request-delay-seconds",
            "0",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "row_count=1" in result.stdout
    manifest = read_json(data_dir / "manifests/trade_xyz_signal_candles_manifest.json")
    assert manifest["request_delay_seconds"] == 0
    assert manifest["notes"] == [
        "Signal candles are historical OHLCV inputs for strategy signals.",
        "Do not use these candles as fill snapshots; fill modeling uses quote snapshots.",
    ]


def test_collect_trade_xyz_signal_candles_subset_rerun_preserves_other_rows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    client = FakeCandleClient()

    collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m", "4h"],
        period_days=1,
        request_delay_seconds=0,
        client=client,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    manifest = collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["4h"],
        period_days=1,
        request_delay_seconds=0,
        client=client,
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    frame = pl.read_parquet(data_dir / "normalized/trade_xyz_signal_candles.parquet")
    assert sorted(frame.get_column("interval").unique().to_list()) == ["30m", "4h"]
    assert manifest["row_count"] == 2
    assert manifest["new_row_count"] == 1
    assert manifest["symbols"] == ["SP500"]


def test_collect_trade_xyz_signal_candles_preserves_failed_existing_key(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m", "4h"],
        period_days=1,
        request_delay_seconds=0,
        retry_delay_seconds=0,
        client=FakeCandleClient(),
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    raw_4h = data_dir / "raw/candles/trade_xyz/4h/SP500.json"
    previous_raw_4h = raw_4h.read_text(encoding="utf-8")
    client = ControlledCandleClient(
        failures_before_success={("xyz:SP500", "4h"): 2},
    )

    manifest = collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m", "4h"],
        period_days=1,
        request_delay_seconds=0,
        retry_delay_seconds=0,
        client=client,
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    frame = pl.read_parquet(data_dir / "normalized/trade_xyz_signal_candles.parquet")
    assert sorted(frame.get_column("interval").to_list()) == ["30m", "4h"]
    assert raw_4h.read_text(encoding="utf-8") == previous_raw_4h
    assert manifest["request_error_count"] == 1
    assert manifest["failed_keys"] == [{"canonical_symbol": "SP500", "interval": "4h"}]
    assert manifest["preserved_existing_row_count"] == 1
    assert manifest["replaced_key_count"] == 1
    assert manifest["artifacts"]["raw_candle_errors_root"].endswith("raw/candles/trade_xyz_errors")


def test_collect_trade_xyz_signal_candles_retries_failed_subset(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    client = ControlledCandleClient(
        failures_before_success={("xyz:SP500", "30m"): 1},
    )

    manifest = collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m"],
        period_days=1,
        request_delay_seconds=0,
        retry_delay_seconds=0,
        client=client,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert client.call_counts[("xyz:SP500", "30m")] == 2
    assert manifest["request_error_count"] == 0
    assert manifest["retry_attempt_count"] == 1
    assert manifest["retry_success_count"] == 1
    assert manifest["successful_request_count"] == 1
    assert manifest["failed_keys"] == []


def test_collect_trade_xyz_signal_candles_empty_success_replaces_existing_key(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m"],
        period_days=1,
        request_delay_seconds=0,
        retry_delay_seconds=0,
        client=FakeCandleClient(),
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    client = ControlledCandleClient(empty_success_keys={("xyz:SP500", "30m")})

    manifest = collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m"],
        period_days=1,
        request_delay_seconds=0,
        retry_delay_seconds=0,
        client=client,
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    frame = pl.read_parquet(data_dir / "normalized/trade_xyz_signal_candles.parquet")
    raw = read_json(data_dir / "raw/candles/trade_xyz/30m/SP500.json")
    assert frame.is_empty()
    assert raw["payload"] == []
    assert manifest["request_error_count"] == 0
    assert manifest["successful_request_count"] == 1
    assert manifest["replaced_key_count"] == 1


def test_signal_candles_manifest_is_fresh_checks_symbols_intervals_and_age(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    client = FakeCandleClient()
    collect_trade_xyz_signal_candles(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m", "4h"],
        period_days=1,
        request_delay_seconds=0,
        client=client,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    fresh, details = signal_candles_manifest_is_fresh(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m", "4h"],
        max_age_hours=24,
        now=datetime(2026, 5, 31, 1, tzinfo=UTC),
    )
    assert fresh is True
    assert details["reason"] == "signal_candles_fresh"

    fresh, details = signal_candles_manifest_is_fresh(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["1d"],
        max_age_hours=24,
        now=datetime(2026, 5, 31, 1, tzinfo=UTC),
    )
    assert fresh is False
    assert details["reason"] == "signal_candle_intervals_missing"

    fresh, details = signal_candles_manifest_is_fresh(
        data_dir=data_dir,
        symbols=["SP500"],
        intervals=["30m"],
        max_age_hours=0.5,
        now=datetime(2026, 5, 31, 1, tzinfo=UTC),
    )
    assert fresh is False
    assert details["reason"] == "signal_candle_manifest_stale"


def test_signal_candles_freshness_uses_parquet_symbols_after_subset_manifest(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    parquet_path = data_dir / "normalized/trade_xyz_signal_candles.parquet"
    parquet_path.parent.mkdir(parents=True)
    rows = []
    for symbol in ("SP500", "META"):
        rows.append(
            {
                "schema_version": "trade_xyz_signal_candle.v1",
                "ts_open": "2026-05-31T00:00:00+00:00",
                "ts_close": "2026-05-31T00:29:59+00:00",
                "canonical_symbol": symbol,
                "venue_symbol": symbol,
                "coin": f"xyz:{symbol}",
                "interval": "30m",
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 1.0,
                "trade_count": 1,
                "source": "hyperliquid_info_candleSnapshot",
                "source_time_open_ms": 1,
                "source_time_close_ms": 2,
                "raw_payload_sha256": symbol.lower(),
                "raw_payload_ref": f"fixture://{symbol.lower()}",
            }
        )
    pl.DataFrame(rows, schema=SIGNAL_CANDLE_SCHEMA).write_parquet(parquet_path)
    manifest_path = data_dir / "manifests/trade_xyz_signal_candles_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "trade_xyz_signal_candles_manifest.v1",
                "generated_at": "2026-05-31T00:00:00+00:00",
                "row_count": 2,
                "symbol_count": 2,
                "requested_symbols": ["META"],
                "intervals": ["30m"],
                "request_error_count": 0,
                "artifacts": {"normalized_signal_candles": str(parquet_path)},
            }
        ),
        encoding="utf-8",
    )

    fresh, details = signal_candles_manifest_is_fresh(
        data_dir=data_dir,
        symbols=["SP500", "META"],
        intervals=["30m"],
        max_age_hours=24,
        now=datetime(2026, 5, 31, 1, tzinfo=UTC),
    )

    assert fresh is True
    assert details["symbols"] == ["META", "SP500"]
