import json
from datetime import datetime, timezone
from pathlib import Path

from sis.models import InstrumentSpec
from sis.storage.jsonl_store import read_jsonl
from sis.storage.normalize import normalize_quotes
from sis.venues.trade_xyz.collector import collect_trade_xyz_quotes


def _fixture(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _active_instrument() -> InstrumentSpec:
    return InstrumentSpec(
        venue="trade_xyz",
        canonical_symbol="NVDA",
        venue_symbol="NVDA",
        asset_class="equity",
        dex="xyz",
        coin="xyz:NVDA",
        asset_id=130002,
        real_market_symbol="NVDA",
        api_readable=True,
        api_orderable=True,
        active=True,
    )


def test_collector_writes_jsonl_with_raw_hash(tmp_path) -> None:
    out_path = tmp_path / "data/raw/quotes/trade_xyz/2026-05-26.jsonl"
    count = collect_trade_xyz_quotes(
        instruments=[_active_instrument()],
        out_path=out_path,
        all_mids_payload={"xyz:NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )
    assert count == 1
    rows = list(read_jsonl(out_path))
    assert len(rows) == 1
    assert rows[0]["raw_payload_sha256"]


def test_collector_enriches_quote_from_meta_and_asset_ctxs(tmp_path) -> None:
    out_path = tmp_path / "data/raw/quotes/trade_xyz/2026-05-26.jsonl"
    count = collect_trade_xyz_quotes(
        instruments=[_active_instrument()],
        out_path=out_path,
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
                    "prevDayPx": "99.0",
                    "dayNtlVlm": "4567",
                }
            ],
        ),
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )
    rows = list(read_jsonl(out_path))

    assert count == 1
    assert rows[0]["mark_price"] == 100.2
    assert rows[0]["oracle_price"] == 100.1
    assert rows[0]["index_price"] == 100.15
    assert rows[0]["funding_rate"] == -0.00001
    assert rows[0]["open_interest_usd"] == 1234.0
    assert rows[0]["bid_depth_10bps_usd"] > 0
    assert rows[0]["ask_depth_10bps_usd"] > 0
    assert "BLOCK_API_ERROR" not in rows[0]["block_reasons"]


def test_normalize_quotes_accepts_trade_xyz_v2(tmp_path) -> None:
    out_path = tmp_path / "data/raw/quotes/trade_xyz/2026-05-26.jsonl"
    collect_trade_xyz_quotes(
        instruments=[_active_instrument()],
        out_path=out_path,
        all_mids_payload={"xyz:NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )
    count = normalize_quotes(
        tmp_path / "data/raw/quotes",
        tmp_path / "data/normalized/quotes.parquet",
        tmp_path / "data/normalized/sis.duckdb",
    )
    assert count == 1
    assert (tmp_path / "data/normalized/quotes.parquet").exists()
    assert (tmp_path / "data/normalized/sis.duckdb").exists()
