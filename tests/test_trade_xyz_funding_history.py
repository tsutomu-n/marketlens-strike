import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
from jsonschema import validate
from typer.testing import CliRunner

from sis.cli import app
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.funding_history import (
    build_trade_xyz_backtest_funding_events_from_history,
    collect_trade_xyz_funding_history,
)


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "venue": "trade_xyz",
                    "canonical_symbol": "XYZ100",
                    "venue_symbol": "XYZ100",
                    "asset_class": "basket_index",
                    "dex": "xyz",
                    "coin": "xyz:XYZ100",
                    "active": True,
                }
            ]
        ),
        encoding="utf-8",
    )


class FakeClient:
    def __init__(self) -> None:
        self.requests = []

    def funding_history(self, coin: str, *, start_time_ms: int, end_time_ms: int | None = None):
        self.requests.append((coin, start_time_ms, end_time_ms))
        return [
            {
                "coin": coin,
                "fundingRate": "-0.00022196",
                "premium": "-0.00052196",
                "time": 1683849600076,
            }
        ]

    def close(self):
        return None


def test_collect_trade_xyz_funding_history_writes_public_history_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    client = FakeClient()

    manifest = collect_trade_xyz_funding_history(
        data_dir=data_dir,
        symbols=["XYZ100"],
        start_time_ms=1683849600000,
        end_time_ms=1683853200000,
        client=client,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert client.requests == [("xyz:XYZ100", 1683849600000, 1683853200000)]
    assert manifest["row_count"] == 1
    assert manifest["usable_as_backtest_funding_event"] is False
    assert (data_dir / "raw/funding_history/trade_xyz/2026-05-31.jsonl").exists()
    assert (data_dir / "normalized/funding_history_events.parquet").exists()
    assert (data_dir / "manifests/funding_history_manifest.json").exists()

    row = pl.read_parquet(data_dir / "normalized/funding_history_events.parquet").row(0, named=True)
    assert row["schema_version"] == "funding_history_event.v1"
    assert row["canonical_symbol"] == "XYZ100"
    assert row["coin"] == "xyz:XYZ100"
    assert row["oracle_price_at_funding"] is None
    assert row["usable_as_backtest_funding_event"] is False
    validate(row, read_json(Path("schemas/funding_history_event.v1.schema.json")))


def test_collect_trade_xyz_funding_history_cli_writes_manifest(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")

    class ContextClient(FakeClient):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("sis.commands.quotes.TradeXyzClient", ContextClient)

    result = CliRunner().invoke(
        app,
        [
            "collect-trade-xyz-funding-history",
            "--symbols",
            "XYZ100",
            "--start-time-ms",
            "1683849600000",
            "--end-time-ms",
            "1683853200000",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "row_count=1" in result.stdout
    assert "usable_as_backtest_funding_event=False" in result.stdout


def _write_raw_quote(
    path: Path,
    *,
    ts_client: str,
    oracle_price: float = 100.25,
    oracle_ts_ms: int = 1683849600076,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "ts_client": ts_client,
                "venue": "trade_xyz",
                "canonical_symbol": "XYZ100",
                "venue_symbol": "XYZ100",
                "source": "trade_xyz_test_quote",
                "raw_payload_sha256": "quote-hash-1",
                "recv_ts_ms": 1683849600100,
                "source_ts_ms": 1683849600100,
                "oracle_ts_ms": oracle_ts_ms,
                "oracle_ts_source": "asset_ctx.oracleTs",
                "oracle_ts_status": "observed",
                "dex": "xyz",
                "coin": "xyz:XYZ100",
                "oracle_price": oracle_price,
                "raw_payload_ref": str(path) + "#row=0",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_backtest_funding_events_from_history_joins_nearest_oracle_quote(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    collect_trade_xyz_funding_history(
        data_dir=data_dir,
        symbols=["XYZ100"],
        start_time_ms=1683849600000,
        end_time_ms=1683853200000,
        client=FakeClient(),
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    _write_raw_quote(
        data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl",
        ts_client="2023-05-12T00:00:00.100000+00:00",
    )

    manifest = build_trade_xyz_backtest_funding_events_from_history(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["row_count"] == 1
    assert manifest["usable_as_backtest_funding_event"] is True
    assert manifest["skipped"]["missing_oracle_quote_within_lag"] == 0
    assert (data_dir / "raw/funding/trade_xyz_from_history/2026-05-31.jsonl").exists()
    assert (data_dir / "normalized/funding_events_from_history.parquet").exists()
    assert (data_dir / "manifests/funding_history_join_manifest.json").exists()

    row = pl.read_parquet(data_dir / "normalized/funding_events_from_history.parquet").row(
        0, named=True
    )
    assert row["schema_version"] == "funding_event.v1"
    assert row["canonical_symbol"] == "XYZ100"
    assert row["funding_interval_minutes"] == 60
    assert row["funding_rate"] == -0.00022196
    assert row["oracle_price_at_funding"] == 100.25
    assert row["oracle_join_ts_source"] == "oracle_ts_ms"
    assert row["oracle_join_lag_seconds"] == 0.0
    assert "|oracle_ref=" in row["raw_payload_ref"]
    validate(row, read_json(Path("schemas/funding_event.v1.schema.json")))


def test_build_backtest_funding_events_from_history_skips_when_oracle_quote_too_far(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    collect_trade_xyz_funding_history(
        data_dir=data_dir,
        symbols=["XYZ100"],
        start_time_ms=1683849600000,
        end_time_ms=1683853200000,
        client=FakeClient(),
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    _write_raw_quote(
        data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl",
        ts_client="2023-05-12T03:00:00+00:00",
        oracle_ts_ms=1683860400000,
    )

    manifest = build_trade_xyz_backtest_funding_events_from_history(
        data_dir=data_dir,
        max_oracle_lag_minutes=1,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["row_count"] == 0
    assert manifest["usable_as_backtest_funding_event"] is False
    assert manifest["skipped"]["missing_oracle_quote_within_lag"] == 1
    assert (data_dir / "normalized/funding_events_from_history.parquet").exists()


def test_build_backtest_funding_events_from_history_cli_writes_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    collect_trade_xyz_funding_history(
        data_dir=data_dir,
        symbols=["XYZ100"],
        start_time_ms=1683849600000,
        end_time_ms=1683853200000,
        client=FakeClient(),
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    _write_raw_quote(
        data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl",
        ts_client="2023-05-12T00:00:00.100000+00:00",
    )

    result = CliRunner().invoke(
        app,
        ["build-trade-xyz-funding-events-from-history"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "artifact_path=" in result.stdout
    assert "row_count=1" in result.stdout
    assert "usable_as_backtest_funding_event=True" in result.stdout
