import json
from pathlib import Path

from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.registry import (
    build_trade_xyz_registry,
    resolve_asset_id,
    write_trade_xyz_registry,
)
from sis.venues.trade_xyz.report import (
    build_trade_xyz_universe_report,
    write_trade_xyz_universe_report,
)


def _fixture(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_resolve_asset_id_formula() -> None:
    assert resolve_asset_id(3, 11) == 130011


def test_trade_xyz_seed_symbols_are_expected() -> None:
    result = build_trade_xyz_registry(
        Path("configs/instrument_registry.seed.json"),
        all_mids_payload=_fixture("tests/fixtures/trade_xyz_all_mids.sample.json"),
        meta_payload=_fixture("tests/fixtures/trade_xyz_meta.sample.json"),
    )
    symbols = {item.canonical_symbol for item in result.instruments if item.active}
    assert symbols == {
        "SP500",
        "XYZ100",
        "NVDA",
        "AAPL",
        "MSFT",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "AMD",
        "EWJ",
    }


def test_trade_xyz_registry_resolves_perp_dex_index_from_perp_dexs() -> None:
    meta_payload = _fixture("tests/fixtures/trade_xyz_meta.sample.json")
    meta_payload.pop("perpDexIndex")
    result = build_trade_xyz_registry(
        Path("configs/instrument_registry.seed.json"),
        all_mids_payload=_fixture("tests/fixtures/trade_xyz_all_mids.sample.json"),
        meta_payload=meta_payload,
        perp_dexs_payload=_fixture("tests/fixtures/trade_xyz_perp_dexs.sample.json"),
    )
    by_symbol = {item.canonical_symbol: item for item in result.instruments}

    assert by_symbol["SP500"].perp_dex_index == 2
    assert by_symbol["SP500"].index_in_meta == 0
    assert by_symbol["SP500"].asset_id == 120000
    assert by_symbol["SP500"].api_orderable is True


def test_trade_xyz_registry_fails_closed_when_perp_dex_index_missing() -> None:
    meta_payload = _fixture("tests/fixtures/trade_xyz_meta.sample.json")
    meta_payload.pop("perpDexIndex")
    result = build_trade_xyz_registry(
        Path("configs/instrument_registry.seed.json"),
        all_mids_payload=_fixture("tests/fixtures/trade_xyz_all_mids.sample.json"),
        meta_payload=meta_payload,
        perp_dexs_payload=[None, {"name": "other"}],
    )
    by_symbol = {item.canonical_symbol: item for item in result.instruments}

    assert by_symbol["SP500"].perp_dex_index is None
    assert by_symbol["SP500"].asset_id is None
    assert by_symbol["SP500"].api_orderable is False


def test_trade_xyz_registry_marks_unresolved_asset_as_not_orderable() -> None:
    meta_payload = _fixture("tests/fixtures/trade_xyz_meta.sample.json")
    meta_payload["universe"] = [row for row in meta_payload["universe"] if row.get("name") != "EWJ"]
    result = build_trade_xyz_registry(
        Path("configs/instrument_registry.seed.json"),
        all_mids_payload=_fixture("tests/fixtures/trade_xyz_all_mids.sample.json"),
        meta_payload=meta_payload,
    )
    by_symbol = {item.canonical_symbol: item for item in result.instruments}
    assert by_symbol["EWJ"].asset_id is None
    assert by_symbol["EWJ"].api_orderable is False


def test_trade_xyz_registry_excludes_crypto_beta_symbols_from_live(tmp_path) -> None:
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps(
            {
                "venues": {
                    "trade_xyz": [
                        {
                            "venue": "trade_xyz",
                            "canonical_symbol": "COIN",
                            "venue_symbol": "COIN",
                            "asset_class": "crypto_beta_equity",
                            "api_readable": True,
                            "api_orderable": False,
                            "active": True,
                            "notes": [],
                        },
                        {
                            "venue": "trade_xyz",
                            "canonical_symbol": "NVDA",
                            "venue_symbol": "NVDA",
                            "asset_class": "equity",
                            "api_readable": True,
                            "api_orderable": False,
                            "active": True,
                            "notes": [],
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    result = build_trade_xyz_registry(
        seed_path,
        all_mids_payload={"xyz:COIN": "1", "xyz:NVDA": "2"},
        meta_payload={"perpDexIndex": 1, "universe": [{"name": "COIN"}, {"name": "NVDA"}]},
    )
    by_symbol = {item.canonical_symbol: item for item in result.instruments}
    assert by_symbol["COIN"].active is False
    assert by_symbol["COIN"].api_orderable is False
    assert by_symbol["NVDA"].active is True


def test_trade_xyz_registry_and_report_are_generated(tmp_path) -> None:
    build_result = build_trade_xyz_registry(
        Path("configs/instrument_registry.seed.json"),
        all_mids_payload=_fixture("tests/fixtures/trade_xyz_all_mids.sample.json"),
        meta_payload=_fixture("tests/fixtures/trade_xyz_meta.sample.json"),
    )
    registry_path = tmp_path / "data/registry/trade_xyz_instrument_registry.json"
    report_path = tmp_path / "data/reports/trade_xyz_universe_report.md"
    write_trade_xyz_registry(registry_path, build_result)
    write_trade_xyz_universe_report(report_path, build_trade_xyz_universe_report(build_result))

    registry = read_json(registry_path)
    assert isinstance(registry, list)
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "excluded symbols" in report_text.lower()
