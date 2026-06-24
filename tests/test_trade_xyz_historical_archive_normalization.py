import json

import pytest

from sis.models import InstrumentSpec
from sis.venues.trade_xyz.historical_archive_normalization import archive_quote_output_path
from sis.venues.trade_xyz.historical_archive_normalization import extract_l2_payload
from sis.venues.trade_xyz.historical_archive_normalization import load_asset_ctxs
from sis.venues.trade_xyz.historical_archive_normalization import load_l2_rows
from sis.venues.trade_xyz.historical_archive_normalization import normalize_symbol
from sis.venues.trade_xyz.historical_archive_normalization import resolve_instrument
from sis.venues.trade_xyz.historical_archive_normalization import source_ts_ms_from_payload


def test_historical_archive_payload_helpers_handle_nested_rows_and_timestamps() -> None:
    nested = {"data": {"time": "1770000000000", "levels": [[{"px": "1"}], [{"px": "2"}]]}}

    payload = extract_l2_payload(nested)

    assert payload == nested["data"]
    assert source_ts_ms_from_payload(payload) == 1770000000000
    assert source_ts_ms_from_payload({"time": True, "timestamp": "1770000000001"}) == (
        1770000000001
    )
    assert source_ts_ms_from_payload({"time": "not-int"}) is None
    assert normalize_symbol("xyz:sp500") == "SP500"
    assert normalize_symbol(None) is None


def test_load_l2_rows_and_asset_ctxs_support_json_and_csv_shapes(tmp_path) -> None:
    l2_path = tmp_path / "archive.jsonl"
    l2_path.write_text(
        json.dumps({"time": 1770000000000, "levels": []}) + "\n\n[]\n",
        encoding="utf-8",
    )
    json_ctx_path = tmp_path / "ctxs.json"
    json_ctx_path.write_text(
        json.dumps({"ctxs": [{"coin": "xyz:XYZ100", "markPx": "100.2"}]}),
        encoding="utf-8",
    )
    csv_ctx_path = tmp_path / "ctxs.csv"
    csv_ctx_path.write_text(
        'coin,markPx,oraclePx,ctx\nxyz:SP500,5000.1,4999.9,"{""funding"": ""-0.01""}"\n',
        encoding="utf-8",
    )

    assert load_l2_rows(l2_path) == [{"time": 1770000000000, "levels": []}]
    assert load_asset_ctxs(json_ctx_path)["XYZ100"] == {
        "coin": "xyz:XYZ100",
        "markPx": "100.2",
    }
    assert load_asset_ctxs(csv_ctx_path)["SP500"] == {"funding": "-0.01"}


def test_resolve_instrument_uses_symbol_coin_and_normalized_coin_fallback() -> None:
    instruments = [
        InstrumentSpec(
            venue="trade_xyz",
            canonical_symbol="XYZ100",
            venue_symbol="XYZ100",
            asset_class="basket_index",
            coin="xyz:XYZ100",
        ),
        InstrumentSpec(
            venue="trade_xyz",
            canonical_symbol="SP500",
            venue_symbol="SP500",
            asset_class="basket_index",
            coin="xyz:SP500",
        ),
    ]

    assert (
        resolve_instrument(instruments, canonical_symbol="XYZ100", coin=None).canonical_symbol
        == "XYZ100"
    )
    assert resolve_instrument(
        instruments, canonical_symbol=None, coin="xyz:SP500"
    ).canonical_symbol == ("SP500")
    assert resolve_instrument(
        instruments, canonical_symbol=None, coin="SP500"
    ).canonical_symbol == ("SP500")
    with pytest.raises(ValueError, match="not found"):
        resolve_instrument(instruments, canonical_symbol=None, coin="UNKNOWN")


def test_archive_quote_output_path_preserves_existing_flat_filename_shape(tmp_path) -> None:
    path = archive_quote_output_path(
        tmp_path / "data",
        {"date": "2026-05-01", "hour": 9, "coin": "xyz:XYZ100"},
    )

    assert str(path).endswith(
        "data/raw/quotes/trade_xyz/historical_archive_20260501_9_xyz_XYZ100.jsonl"
    )
