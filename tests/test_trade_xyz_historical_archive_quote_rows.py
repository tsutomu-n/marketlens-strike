from __future__ import annotations

from pathlib import Path

from sis.models import InstrumentSpec
from sis.venues.trade_xyz.historical_archive_quote_rows import (
    build_historical_archive_quote_row,
)


def _instrument() -> InstrumentSpec:
    return InstrumentSpec(
        venue="trade_xyz",
        canonical_symbol="XYZ100",
        venue_symbol="XYZ100",
        asset_class="basket_index",
        real_market_symbol="XYZ",
        coin="xyz:XYZ100",
        asset_id=42,
        fee_mode="fixed_bps",
        taker_fee_bps=9.0,
        maker_fee_bps=3.0,
    )


def _archive_row() -> dict:
    return {
        "data": {
            "coin": "xyz:XYZ100",
            "time": 1770000000000,
            "levels": [
                [{"px": "100.0", "sz": "9"}],
                [{"px": "100.2", "sz": "11"}],
            ],
        }
    }


def test_build_historical_archive_quote_row_with_asset_ctx() -> None:
    result = build_historical_archive_quote_row(
        row=_archive_row(),
        instrument=_instrument(),
        effective_coin="xyz:XYZ100",
        asset_ctx={"markPx": "100.2", "oraclePx": "100.1", "funding": "-0.00001"},
        output_path=Path("data/raw/quotes/trade_xyz/example.jsonl"),
        row_index=3,
    )

    assert result.skip_reason is None
    assert result.missing_asset_ctx is False
    assert result.quote is not None
    assert result.quote["source"] == "hyperliquid_archive.l2Book+asset_ctxs"
    assert result.quote["ts_client"] == "2026-02-02T02:40:00Z"
    assert result.quote["mark_price"] == 100.2
    assert result.quote["oracle_price"] == 100.1
    assert result.quote["raw_payload_ref"] == "data/raw/quotes/trade_xyz/example.jsonl#row=3"
    assert "BLOCK_HISTORICAL_ASSET_CTX_MISSING" not in result.quote["block_reasons"]


def test_build_historical_archive_quote_row_marks_missing_asset_ctx_not_tradable() -> None:
    result = build_historical_archive_quote_row(
        row=_archive_row(),
        instrument=_instrument(),
        effective_coin="xyz:XYZ100",
        asset_ctx=None,
        output_path=Path("data/raw/quotes/trade_xyz/example.jsonl"),
        row_index=0,
    )

    assert result.skip_reason is None
    assert result.missing_asset_ctx is True
    assert result.quote is not None
    assert result.quote["is_tradable"] is False
    assert "BLOCK_HISTORICAL_ASSET_CTX_MISSING" in result.quote["block_reasons"]


def test_build_historical_archive_quote_row_reports_existing_skip_reasons() -> None:
    assert (
        build_historical_archive_quote_row(
            row=[],
            instrument=_instrument(),
            effective_coin="xyz:XYZ100",
            asset_ctx=None,
            output_path=Path("out.jsonl"),
            row_index=0,
        ).skip_reason
        == "invalid_json_object"
    )
    assert (
        build_historical_archive_quote_row(
            row={"data": {"time": 1770000000000}},
            instrument=_instrument(),
            effective_coin="xyz:XYZ100",
            asset_ctx=None,
            output_path=Path("out.jsonl"),
            row_index=0,
        ).skip_reason
        == "missing_levels"
    )
    assert (
        build_historical_archive_quote_row(
            row={"levels": [[{"px": "100"}], [{"px": "101"}]]},
            instrument=_instrument(),
            effective_coin="xyz:XYZ100",
            asset_ctx=None,
            output_path=Path("out.jsonl"),
            row_index=0,
        ).skip_reason
        == "missing_source_ts_ms"
    )
