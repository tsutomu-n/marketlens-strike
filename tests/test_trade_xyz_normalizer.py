import json
from datetime import datetime, timezone
from pathlib import Path

from sis.venues.trade_xyz.normalizer import compute_book_metrics, payload_hash, quote_from_l2_book


def _fixture_payload() -> dict:
    return json.loads(Path("tests/fixtures/trade_xyz_l2_book.sample.json").read_text(encoding="utf-8"))


def test_l2_book_to_quote_log_computes_spread_and_depth() -> None:
    payload = _fixture_payload()
    quote = quote_from_l2_book(
        canonical_symbol="NVDA",
        coin="xyz:NVDA",
        asset_id=130002,
        real_market_symbol="NVDA",
        payload=payload,
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )
    assert quote.best_bid == 99.9
    assert quote.best_ask == 100.1
    assert round(quote.mid_price or 0, 2) == 100.0
    assert round(quote.spread_bps or 0, 2) == 20.0
    assert (quote.depth_10bps_usd or 0) > 0
    assert (quote.depth_25bps_usd or 0) > 0


def test_missing_book_side_sets_not_tradable() -> None:
    payload = {"levels": [[{"px": "99.9", "sz": "10"}], []]}
    metrics = compute_book_metrics(payload)
    assert "BLOCK_NO_ASK" in metrics.block_reasons
    quote = quote_from_l2_book(
        canonical_symbol="NVDA",
        coin="xyz:NVDA",
        asset_id=130002,
        real_market_symbol="NVDA",
        payload=payload,
    )
    assert quote.is_tradable is False
    assert quote.market_status.value == "unknown"
    assert "BLOCK_NO_ASK" in quote.block_reasons


def test_raw_payload_hash_is_stable() -> None:
    payload = _fixture_payload()
    assert payload_hash(payload) == payload_hash(dict(payload))
