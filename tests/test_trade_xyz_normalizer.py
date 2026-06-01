import json
from datetime import datetime, timezone
from pathlib import Path

from sis.venues.trade_xyz.normalizer import compute_book_metrics, payload_hash, quote_from_l2_book


def _fixture_payload() -> dict:
    return json.loads(
        Path("tests/fixtures/trade_xyz_l2_book.sample.json").read_text(encoding="utf-8")
    )


def test_l2_book_to_quote_log_computes_spread_and_depth() -> None:
    payload = _fixture_payload()
    now = datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc)
    quote = quote_from_l2_book(
        canonical_symbol="NVDA",
        coin="xyz:NVDA",
        asset_id=130002,
        real_market_symbol="NVDA",
        payload=payload,
        fee_mode="standard",
        taker_fee_bps=9.0,
        maker_fee_bps=3.0,
        asset_ctx={"oraclePx": "100.1", "oracleTs": "1770000000000"},
        now=now,
    )
    assert quote.best_bid == 99.9
    assert quote.best_ask == 100.1
    assert round(quote.mid_price or 0, 2) == 100.0
    assert round(quote.spread_bps or 0, 2) == 20.0
    assert (quote.depth_10bps_usd or 0) > 0
    assert (quote.depth_25bps_usd or 0) > 0
    assert quote.fee_mode == "standard"
    assert quote.taker_fee_bps == 9.0
    assert quote.maker_fee_bps == 3.0
    assert quote.oracle_ts_ms == 1770000000000
    assert quote.oracle_ts_source == "oracleTs"
    assert quote.oracle_ts_status == "observed"
    assert quote.oracle_ts_missing_reason is None
    assert quote.oracle_freshness_source_ts_ms == payload["time"]
    assert quote.oracle_freshness_recv_ts_ms == int(now.timestamp() * 1000)
    assert quote.oracle_freshness_lag_ms == int(now.timestamp() * 1000) - payload["time"]
    assert quote.oracle_freshness_status == "observed_snapshot_lag"
    assert "not oracle_ts_ms" in (quote.oracle_freshness_note or "")


def test_l2_book_to_quote_log_records_missing_oracle_timestamp_reason() -> None:
    quote = quote_from_l2_book(
        canonical_symbol="NVDA",
        coin="xyz:NVDA",
        asset_id=130002,
        real_market_symbol="NVDA",
        payload=_fixture_payload(),
        asset_ctx={"oraclePx": "100.1"},
    )

    assert quote.oracle_ts_ms is None
    assert quote.oracle_ts_status == "missing"
    assert quote.oracle_ts_missing_reason == "asset_ctx_missing_oracle_timestamp_field"
    assert quote.oracle_freshness_status == "observed_snapshot_lag"
    assert quote.oracle_freshness_lag_ms is not None


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
