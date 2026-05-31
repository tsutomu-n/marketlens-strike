import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
from jsonschema import validate
from typer.testing import CliRunner

from sis.cli import app
from sis.market_calendar import market_session_state
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.session_state import build_trade_xyz_session_state_observations


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


def _quote(ts: datetime) -> dict:
    return {
        "ts_client": ts.isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "SP500",
        "venue_symbol": "SP500",
        "source": "test",
        "raw_payload_sha256": f"hash-{int(ts.timestamp())}",
        "raw_payload_ref": "fixture://quote",
    }


def _write_quotes(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_market_session_state_marks_xnys_regular_and_holiday() -> None:
    regular = market_session_state("trade_xyz", "SP500", datetime(2026, 5, 26, 14, 0, tzinfo=UTC))
    holiday = market_session_state("trade_xyz", "SP500", datetime(2026, 5, 25, 14, 0, tzinfo=UTC))

    assert regular.calendar == "XNYS"
    assert regular.session_type == "regular"
    assert regular.external_session_open is True
    assert regular.holiday_closure is False
    assert holiday.session_type == "closed"
    assert holiday.external_session_open is False
    assert holiday.holiday_closure is True


def test_trade_xyz_session_state_derives_internal_and_maintenance_windows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_quotes(
        data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl",
        [
            _quote(datetime(2026, 5, 26, 14, 0, tzinfo=UTC)),
            _quote(datetime(2026, 5, 26, 21, 30, tzinfo=UTC)),
        ],
    )

    manifest = build_trade_xyz_session_state_observations(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["missing_field_counts"] == {}
    frame = pl.read_parquet(data_dir / "normalized/session_state_observations.parquet").sort(
        "observed_ts"
    )
    regular, maintenance = frame.to_dicts()
    assert regular["source"] == "docs_trade_xyz_specification_index"
    assert regular["data_status"] == "spec_derived"
    assert regular["external_session_open"] is True
    assert regular["internal_session_open"] is False
    assert regular["maintenance_window"] is False
    assert maintenance["external_session_open"] is False
    assert maintenance["internal_session_open"] is True
    assert maintenance["maintenance_window"] is True


def test_trade_xyz_session_state_writes_artifacts_and_schema_valid_rows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_quotes(
        data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl",
        [
            _quote(datetime(2026, 5, 26, 14, 0, tzinfo=UTC)),
            _quote(datetime(2026, 5, 25, 14, 0, tzinfo=UTC)),
        ],
    )

    manifest = build_trade_xyz_session_state_observations(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["row_count"] == 2
    assert manifest["session_type_counts"] == {"closed": 1, "regular": 1}
    assert manifest["missing_field_counts"] == {}
    assert (data_dir / "raw/sessions/trade_xyz_state/2026-05-31.jsonl").exists()
    assert (data_dir / "normalized/session_state_observations.parquet").exists()
    assert (data_dir / "manifests/session_state_manifest.json").exists()

    row = pl.read_parquet(data_dir / "normalized/session_state_observations.parquet").row(
        0, named=True
    )
    schema = read_json(Path("schemas/session_state_observation.v1.schema.json"))
    validate(row, schema)


def test_trade_xyz_session_state_cli_writes_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_quotes(
        data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl",
        [_quote(datetime(2026, 5, 26, 14, 0, tzinfo=UTC))],
    )

    result = CliRunner().invoke(
        app,
        ["build-trade-xyz-session-state"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "row_count=1" in result.stdout
    assert (data_dir / "manifests/session_state_manifest.json").exists()
