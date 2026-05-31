from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
from jsonschema import validate
from typer.testing import CliRunner

from sis.cli import app
from sis.models import InstrumentSpec
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.collector import collect_trade_xyz_quotes
from sis.venues.trade_xyz.reference_data import build_trade_xyz_reference_datasets


def _fixture(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _instrument() -> InstrumentSpec:
    return InstrumentSpec(
        venue="trade_xyz",
        canonical_symbol="NVDA",
        venue_symbol="NVDA",
        asset_class="equity",
        dex="xyz",
        coin="xyz:NVDA",
        asset_id=130002,
        real_market_symbol="NVDA",
        fee_mode="standard",
        taker_fee_bps=9.0,
        maker_fee_bps=3.0,
        discovery_bound_bps=500.0,
        oi_cap_usd=1_000_000.0,
        external_session="nasdaq_regular",
        internal_session="trade_xyz_internal",
        active=True,
    )


def _write_registry(path: Path, instruments: list[InstrumentSpec]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([item.model_dump(mode="json") for item in instruments]),
        encoding="utf-8",
    )


def test_build_trade_xyz_reference_datasets_writes_required_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    _write_registry(registry_path, [_instrument()])
    collect_trade_xyz_quotes(
        instruments=[_instrument()],
        out_path=data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl",
        all_mids_payload={"NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        meta_and_asset_ctxs_payload=(
            {"universe": [{"name": "xyz:NVDA"}]},
            [
                {
                    "markPx": "100.2",
                    "oraclePx": "100.1",
                    "oracleTs": "1770000000000",
                    "midPx": "100.15",
                    "funding": "-0.00001",
                    "openInterest": "1234",
                    "premium": "-0.1",
                }
            ],
        ),
        now=datetime(2026, 5, 26, 0, 15, tzinfo=timezone.utc),
    )

    manifest = build_trade_xyz_reference_datasets(
        data_dir=data_dir,
        snapshot_ts=datetime(2026, 5, 26, 1, 0, tzinfo=timezone.utc),
    )

    assert manifest["row_counts"]["instrument_registry_snapshots"] == 1
    assert manifest["row_counts"]["fee_snapshots"] == 1
    assert manifest["row_counts"]["session_calendar_snapshots"] == 1
    assert manifest["row_counts"]["funding_events"] == 1
    assert (data_dir / "normalized/instrument_registry_snapshots.parquet").exists()
    assert (data_dir / "normalized/fee_snapshots.parquet").exists()
    assert (data_dir / "normalized/session_calendar_snapshots.parquet").exists()
    assert (data_dir / "normalized/funding_events.parquet").exists()
    assert (data_dir / "raw/fees/trade_xyz/2026-05-26.jsonl").exists()
    assert (data_dir / "raw/sessions/trade_xyz/2026-05-26.jsonl").exists()
    assert (data_dir / "raw/funding/trade_xyz/2026-05-26.jsonl").exists()
    assert (data_dir / "manifests/trade_xyz_reference_datasets_manifest.json").exists()
    assert (data_dir / "manifests/instrument_registry_manifest.json").exists()
    assert (data_dir / "manifests/fee_manifest.json").exists()
    assert (data_dir / "manifests/session_calendar_manifest.json").exists()
    assert (data_dir / "manifests/oracle_timestamp_manifest.json").exists()
    assert (data_dir / "manifests/funding_manifest.json").exists()
    assert manifest["session_missing_field_counts"]["maintenance_window"] == 1
    assert manifest["fee_source"]["account_specific_fee_status"] == (
        "not_collected_no_wallet_or_user_context"
    )
    assert manifest["fee_source"]["account_specific_missing_field_counts"]["builder_fee_bps"] == 1
    assert manifest["oracle_timestamp"]["oracle_ts_present_count"] == 1
    assert manifest["oracle_timestamp"]["oracle_ts_missing_count"] == 0

    fee_manifest = read_json(data_dir / "manifests/fee_manifest.json")
    assert fee_manifest["schema_version"] == "fee_manifest.v1"
    assert fee_manifest["fee_snapshot_count"] == 1
    assert fee_manifest["account_specific_missing_fields"] == [
        "fee_tier",
        "builder_fee_bps",
        "staking_discount_bps",
        "account_growth_mode",
    ]

    funding = pl.read_parquet(data_dir / "normalized/funding_events.parquet").row(0, named=True)
    assert funding["schema_version"] == "funding_event.v1"
    assert funding["canonical_symbol"] == "NVDA"
    assert funding["funding_interval_minutes"] == 60
    assert funding["oracle_price_at_funding"] == 100.1
    assert funding["raw_payload_ref"].endswith("#row=0")
    session = pl.read_parquet(data_dir / "normalized/session_calendar_snapshots.parquet").row(
        0, named=True
    )
    assert session["schema_version"] == "session_calendar_snapshot.v1"
    assert session["external_session_ref"] == "nasdaq_regular"
    assert session["internal_session_ref"] == "trade_xyz_internal"
    assert session["maintenance_window"] is None
    assert "maintenance_window" in session["missing_fields"]


def test_trade_xyz_reference_dataset_rows_match_schemas(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    _write_registry(registry_path, [_instrument()])
    collect_trade_xyz_quotes(
        instruments=[_instrument()],
        out_path=data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl",
        all_mids_payload={"NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        meta_and_asset_ctxs_payload=(
            {"universe": [{"name": "xyz:NVDA"}]},
            [
                {
                    "markPx": "100.2",
                    "oraclePx": "100.1",
                    "funding": "-0.00001",
                    "openInterest": "1234",
                }
            ],
        ),
        now=datetime(2026, 5, 26, 0, 15, tzinfo=timezone.utc),
    )
    build_trade_xyz_reference_datasets(
        data_dir=data_dir,
        snapshot_ts=datetime(2026, 5, 26, 1, 0, tzinfo=timezone.utc),
    )

    schemas = {
        "funding_events.parquet": read_json(Path("schemas/funding_event.v1.schema.json")),
        "fee_snapshots.parquet": read_json(Path("schemas/fee_snapshot.v1.schema.json")),
        "session_calendar_snapshots.parquet": read_json(
            Path("schemas/session_calendar_snapshot.v1.schema.json")
        ),
        "instrument_registry_snapshots.parquet": read_json(
            Path("schemas/instrument_registry_snapshot.v1.schema.json")
        ),
    }
    for name, schema in schemas.items():
        rows = pl.read_parquet(data_dir / f"normalized/{name}").to_dicts()
        assert rows
        validate(rows[0], schema)


def test_build_trade_xyz_reference_data_cli_writes_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    _write_registry(registry_path, [_instrument()])
    collect_trade_xyz_quotes(
        instruments=[_instrument()],
        out_path=data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl",
        all_mids_payload={"NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        meta_and_asset_ctxs_payload=(
            {"universe": [{"name": "xyz:NVDA"}]},
            [
                {
                    "oraclePx": "100.1",
                    "oracleTs": "1770000000000",
                    "funding": "-0.00001",
                    "openInterest": "1234",
                }
            ],
        ),
        now=datetime(2026, 5, 26, 0, 15, tzinfo=timezone.utc),
    )

    result = CliRunner().invoke(
        app,
        ["build-trade-xyz-reference-data"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "fee_snapshots_count=1" in result.stdout
    assert "funding_events_count=1" in result.stdout
    assert (data_dir / "manifests/trade_xyz_reference_datasets_manifest.json").exists()
    assert (data_dir / "manifests/fee_manifest.json").exists()
    assert (data_dir / "manifests/oracle_timestamp_manifest.json").exists()


def test_build_trade_xyz_reference_data_records_oracle_ts_missing_reason(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    _write_registry(registry_path, [_instrument()])
    collect_trade_xyz_quotes(
        instruments=[_instrument()],
        out_path=data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl",
        all_mids_payload={"NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        meta_and_asset_ctxs_payload=(
            {"universe": [{"name": "xyz:NVDA"}]},
            [{"oraclePx": "100.1", "funding": "-0.00001", "openInterest": "1234"}],
        ),
        now=datetime(2026, 5, 26, 0, 15, tzinfo=timezone.utc),
    )

    manifest = build_trade_xyz_reference_datasets(
        data_dir=data_dir,
        snapshot_ts=datetime(2026, 5, 26, 1, 0, tzinfo=timezone.utc),
    )
    oracle_manifest = read_json(data_dir / "manifests/oracle_timestamp_manifest.json")

    assert manifest["oracle_timestamp"]["oracle_ts_missing_count"] == 1
    assert oracle_manifest["oracle_ts_missing_reasons"] == {
        "asset_ctx_missing_oracle_timestamp_field": 1
    }
    assert "source_ts_ms from l2Book is not reused as oracle_ts_ms" in oracle_manifest["notes"]


def test_build_trade_xyz_reference_data_cli_fails_without_raw_quotes(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json", [_instrument()])

    result = CliRunner().invoke(
        app,
        ["build-trade-xyz-reference-data"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 2
    assert "No raw quote JSONL files found" in result.stdout
