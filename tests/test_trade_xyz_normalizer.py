import json
from datetime import datetime, timezone
from pathlib import Path

from sis.venues.trade_xyz.normalizer import compute_book_metrics, payload_hash, quote_from_l2_book
from sis.venues.trade_xyz.normalizer import quote_from_ws_active_asset_ctx_row
from sis.venues.trade_xyz.normalizer import quote_from_ws_bbo_row


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


def test_ws_bbo_row_to_quote_log_builds_fill_snapshot_candidate() -> None:
    row = {
        "subscription": "bbo",
        "channel": "bbo",
        "message_kind": "data",
        "recv_ts_ms": 1780394603762,
        "source_ts_ms": 1780394603466,
        "canonical_symbol": "SP500",
        "venue_symbol": "xyz:SP500",
        "coin": "xyz:SP500",
        "payload_sha256": "sha256:bbo",
        "payload": {
            "channel": "bbo",
            "data": {
                "coin": "xyz:SP500",
                "time": 1780394603466,
                "bbo": [
                    {"px": "7585.5", "sz": "0.575"},
                    {"px": "7585.6", "sz": "7.022"},
                ],
            },
        },
    }

    quote = quote_from_ws_bbo_row(row, asset_id=130001, real_market_symbol="SPX")

    assert quote.source == "trade_xyz_ws_bbo"
    assert quote.canonical_symbol == "SP500"
    assert quote.recv_ts_ms == 1780394603762
    assert quote.source_ts_ms == 1780394603466
    assert quote.best_bid == 7585.5
    assert quote.best_ask == 7585.6
    assert quote.exec_buy_price == 7585.6
    assert quote.exec_sell_price == 7585.5
    assert round(quote.mid_price or 0, 2) == 7585.55
    assert quote.is_tradable is True
    assert quote.block_reasons == []
    assert quote.oracle_ts_ms is None
    assert quote.oracle_ts_status == "missing"
    assert quote.oracle_ts_missing_reason == "asset_ctx_missing"


def test_ws_active_asset_ctx_row_to_quote_log_builds_signal_state_candidate() -> None:
    row = {
        "subscription": "activeAssetCtx",
        "channel": "activeAssetCtx",
        "message_kind": "data",
        "recv_ts_ms": 1780394602433,
        "canonical_symbol": "SP500",
        "venue_symbol": "xyz:SP500",
        "coin": "xyz:SP500",
        "payload_sha256": "sha256:ctx",
        "payload": {
            "channel": "activeAssetCtx",
            "data": {
                "coin": "xyz:SP500",
                "ctx": {
                    "funding": "-0.0000086251",
                    "openInterest": "65020.956",
                    "prevDayPx": "7596.2",
                    "dayNtlVlm": "257731965.5177003145",
                    "premium": "-0.0004424225",
                    "oraclePx": "7588.9",
                    "markPx": "7585.6",
                    "midPx": "7585.55",
                    "impactPxs": ["7585.485", "7585.6"],
                },
            },
        },
    }

    quote = quote_from_ws_active_asset_ctx_row(row)

    assert quote.source == "trade_xyz_ws_activeAssetCtx"
    assert quote.mark_price == 7585.6
    assert quote.oracle_price == 7588.9
    assert quote.index_price == 7585.55
    assert quote.mid_price == 7585.55
    assert quote.funding_rate == -0.0000086251
    assert quote.open_interest_usd == 65020.956
    assert quote.best_bid is None
    assert quote.best_ask is None
    assert quote.is_tradable is False
    assert quote.block_reasons == ["BLOCK_NO_BBO_FILL_SNAPSHOT"]
    assert quote.source_ts_ms is None
    assert quote.oracle_ts_ms is None
    assert quote.oracle_ts_status == "missing"
    assert quote.oracle_ts_missing_reason == "asset_ctx_missing_oracle_timestamp_field"
    assert quote.oracle_freshness_status == "missing_snapshot_timestamp"
    assert quote.oracle_freshness_recv_ts_ms == 1780394602433


def test_ws_active_asset_ctx_does_not_reuse_recv_timestamp_as_oracle_timestamp() -> None:
    quote = quote_from_ws_active_asset_ctx_row(
        {
            "subscription": "activeAssetCtx",
            "channel": "activeAssetCtx",
            "message_kind": "data",
            "recv_ts_ms": 1780394602433,
            "canonical_symbol": "SP500",
            "venue_symbol": "xyz:SP500",
            "coin": "xyz:SP500",
            "payload_sha256": "sha256:ctx",
            "payload": {
                "channel": "activeAssetCtx",
                "data": {
                    "coin": "xyz:SP500",
                    "ctx": {"oraclePx": "7588.9", "markPx": "7585.6", "midPx": "7585.55"},
                },
            },
        }
    )

    assert quote.recv_ts_ms == 1780394602433
    assert quote.oracle_ts_ms is None
    assert quote.oracle_ts_status == "missing"


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
