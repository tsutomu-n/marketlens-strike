from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from jsonschema import validate
import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.research.providers import PriceProvider, ResearchFetchRequest, StooqPriceProvider
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


class SelectiveFakePriceProvider(PriceProvider):
    def __init__(self, *, name: str, returned_symbols: set[str]) -> None:
        self.name = name
        self.returned_symbols = {item.upper() for item in returned_symbols}
        self.requests: list[list[str]] = []

    def fetch_ohlcv(self, request: ResearchFetchRequest) -> pl.DataFrame:
        self.requests.append(list(request.symbols))
        rows: list[dict] = []
        start_ts = datetime(2026, 5, 1, tzinfo=UTC)
        for symbol in request.symbols:
            if symbol.upper() not in self.returned_symbols:
                continue
            rows.append(
                {
                    "ts": start_ts,
                    "symbol": symbol,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.5,
                    "volume": 1000.0,
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


def test_collect_trade_xyz_real_market_reference_uses_provider_chain_for_missing_symbols(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    first = SelectiveFakePriceProvider(name="first", returned_symbols={"^VIX"})
    second = SelectiveFakePriceProvider(name="second", returned_symbols={"SPY"})
    third = SelectiveFakePriceProvider(name="third", returned_symbols={"UUP"})

    manifest = collect_trade_xyz_real_market_reference(
        data_dir=data_dir,
        provider_chain=[first, second, third],
        start=date(2026, 5, 1),
        end=date(2026, 5, 3),
        interval="1d",
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["status"] == "fail"
    assert manifest["provider_chain"] == ["first", "second", "third"]
    assert first.requests == [["SPY", "^VIX", "UUP", "USDJPY=X", "EURUSD=X"]]
    assert second.requests == [["SPY", "UUP", "USDJPY=X", "EURUSD=X"]]
    assert third.requests == [["UUP", "USDJPY=X", "EURUSD=X"]]
    assert manifest["resolved_by_provider"]["^VIX"] == "first"
    assert manifest["resolved_by_provider"]["SPY"] == "second"
    assert manifest["resolved_by_provider"]["UUP"] == "third"
    assert manifest["missing_mapped_symbols"] == []
    assert manifest["unresolved_symbols"] == ["EURUSD=X", "USDJPY=X"]

    frame = pl.read_parquet(data_dir / "normalized/real_market_reference_bars.parquet")
    assert frame.filter(pl.col("real_market_symbol") == "SPY").row(0, named=True)["provider"] == (
        "second"
    )


def test_stooq_price_provider_normalizes_daily_bars() -> None:
    import pandas as pd

    def reader(symbol: str, source: str, start: date, end: date) -> pd.DataFrame:
        assert symbol == "SPY"
        assert source == "stooq"
        assert start == date(2026, 5, 1)
        assert end == date(2026, 5, 3)
        return pd.DataFrame(
            {
                "Open": [101.0, 100.0],
                "High": [102.0, 101.0],
                "Low": [100.0, 99.0],
                "Close": [101.5, 100.5],
                "Volume": [2000.0, 1000.0],
            },
            index=pd.to_datetime(["2026-05-02", "2026-05-01"]),
        )

    frame = StooqPriceProvider(reader=reader).fetch_ohlcv(
        ResearchFetchRequest(
            symbols=["SPY"],
            start=date(2026, 5, 1),
            end=date(2026, 5, 3),
            interval="1d",
        )
    )

    assert frame.get_column("symbol").to_list() == ["SPY", "SPY"]
    assert frame.get_column("provider").to_list() == ["stooq", "stooq"]
    assert frame.get_column("close").to_list() == [100.5, 101.5]


def test_stooq_price_provider_rejects_intraday_interval() -> None:
    provider = StooqPriceProvider(reader=lambda *_args, **_kwargs: None)

    try:
        provider.fetch_ohlcv(
            ResearchFetchRequest(
                symbols=["SPY"],
                start=date(2026, 5, 1),
                end=date(2026, 5, 3),
                interval="30m",
            )
        )
    except ValueError as exc:
        assert "only supports 1d" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported Stooq interval")


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
    assert "provider_chain=fake_price" in result.stdout
    assert "row_count=" in result.stdout
    assert (data_dir / "manifests/trade_xyz_real_market_reference_manifest.json").exists()
