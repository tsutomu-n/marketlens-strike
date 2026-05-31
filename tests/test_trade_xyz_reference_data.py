from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
from jsonschema import validate

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
    assert manifest["row_counts"]["funding_events"] == 1
    assert (data_dir / "normalized/instrument_registry_snapshots.parquet").exists()
    assert (data_dir / "normalized/fee_snapshots.parquet").exists()
    assert (data_dir / "normalized/funding_events.parquet").exists()
    assert (data_dir / "raw/funding/trade_xyz/2026-05-26.jsonl").exists()
    assert (data_dir / "manifests/trade_xyz_reference_datasets_manifest.json").exists()
    assert (data_dir / "manifests/instrument_registry_manifest.json").exists()
    assert (data_dir / "manifests/funding_manifest.json").exists()

    funding = pl.read_parquet(data_dir / "normalized/funding_events.parquet").row(0, named=True)
    assert funding["schema_version"] == "funding_event.v1"
    assert funding["canonical_symbol"] == "NVDA"
    assert funding["funding_interval_minutes"] == 60
    assert funding["oracle_price_at_funding"] == 100.1
    assert funding["raw_payload_ref"].endswith("#row=0")


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
        "instrument_registry_snapshots.parquet": read_json(
            Path("schemas/instrument_registry_snapshot.v1.schema.json")
        ),
    }
    for name, schema in schemas.items():
        rows = pl.read_parquet(data_dir / f"normalized/{name}").to_dicts()
        assert rows
        validate(rows[0], schema)
