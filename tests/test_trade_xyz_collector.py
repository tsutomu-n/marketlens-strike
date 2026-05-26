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
