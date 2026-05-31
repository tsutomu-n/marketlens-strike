from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from jsonschema import validate
import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.research.providers import PriceProvider, ResearchFetchRequest
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.real_market_reference import (
    collect_trade_xyz_real_market_reference,
)


class FakePriceProvider(PriceProvider):
    name = "fake_price"

    def fetch_ohlcv(self, request: ResearchFetchRequest) -> pl.DataFrame:
        rows: list[dict] = []
        start_ts = datetime(2026, 5, 1, tzinfo=UTC)
        for symbol in request.symbols:
            if symbol == "MISSING":
                continue
            for offset in range(2):
                close = 100.0 + offset
                rows.append(
                    {
                        "ts": start_ts + timedelta(days=offset),
                        "symbol": symbol,
                        "open": close - 0.5,
                        "high": close + 1.0,
                        "low": close - 1.0,
                        "close": close,
                        "volume": 1000 + offset,
                        "provider_symbol": symbol,
                        "interval": request.interval,
                        "adjustment": "none",
                    }
                )
        return pl.DataFrame(rows)


def _write_registry(path: Path, *, real_symbol: str = "SPY") -> None:
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
                    "real_market_symbol": real_symbol,
                    "active": True,
                }
            ]
        ),
        encoding="utf-8",
    )


def test_collect_trade_xyz_real_market_reference_writes_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")

    manifest = collect_trade_xyz_real_market_reference(
        data_dir=data_dir,
        provider=FakePriceProvider(),
        start=date(2026, 5, 1),
        end=date(2026, 5, 3),
        interval="1d",
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["status"] == "pass"
    assert manifest["row_count"] > 0
    assert manifest["missing_mapped_symbols"] == []
    assert "SPY" in manifest["requested_symbols"]
    assert "^VIX" in manifest["requested_symbols"]
    assert (data_dir / "normalized/real_market_reference_bars.parquet").exists()
    frame = pl.read_parquet(data_dir / "normalized/real_market_reference_bars.parquet")
    assert "canonical_symbol" in frame.columns
    assert "data_role" in frame.columns
    assert set(frame.get_column("data_role").to_list()) == {
        "underlying_reference",
        "regime_reference",
    }
    validate(
        manifest,
        read_json(Path("schemas/trade_xyz_real_market_reference_manifest.v1.schema.json")),
    )


def test_collect_trade_xyz_real_market_reference_records_missing_mapped_symbol(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json", real_symbol="MISSING")

    manifest = collect_trade_xyz_real_market_reference(
        data_dir=data_dir,
        provider=FakePriceProvider(),
        start=date(2026, 5, 1),
        end=date(2026, 5, 3),
        interval="1d",
    )

    assert manifest["status"] == "fail"
    assert manifest["missing_mapped_symbols"] == ["MISSING"]


def test_collect_trade_xyz_real_market_reference_cli_writes_manifest(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")

    monkeypatch.setattr(
        "sis.venues.trade_xyz.real_market_reference.YahooFinancePriceProvider",
        FakePriceProvider,
    )
    result = CliRunner().invoke(
        app,
        [
            "collect-trade-xyz-real-market-reference",
            "--symbols",
            "SP500",
            "--start",
            "2026-05-01",
            "--end",
            "2026-05-03",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "status=pass" in result.stdout
    assert "row_count=" in result.stdout
    assert (data_dir / "manifests/trade_xyz_real_market_reference_manifest.json").exists()
