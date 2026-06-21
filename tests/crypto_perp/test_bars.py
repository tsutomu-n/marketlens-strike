from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.crypto_perp.bars import (
    build_candle_bars,
    build_candle_history_plan,
    interval_to_milliseconds,
)
from sis.crypto_perp.bitget.normalizers import normalize_tickers
from sis.crypto_perp.heartbeat import build_market_snapshot


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures/crypto_perp/bitget/public"


def test_build_candle_bars_marks_non_final_bar() -> None:
    bars = build_candle_bars(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        candle_rows=[
            {
                "ts_open": "1710000000000",
                "open": "100",
                "high": "110",
                "low": "90",
                "close": "105",
                "base_volume": "10",
                "quote_turnover": "1000",
                "candle_type": "market",
                "interval": "15m",
            },
            {
                "ts_open": str(1710000000000 + interval_to_milliseconds("15m")),
                "open": "105",
                "high": "111",
                "low": "104",
                "close": "108",
                "base_volume": "12",
                "quote_turnover": "1200",
                "candle_type": "market",
                "interval": "15m",
            },
        ],
        ts_ingested="2026-06-21T04:00:00Z",
        source_payload_sha256="f" * 64,
        now_ms=1710000000000 + interval_to_milliseconds("15m") + 60_000,
    )

    assert bars[0].is_final is True
    assert bars[1].is_final is False
    assert bars[0].ts_available.isoformat().startswith("2024-03-09T16:15:00")


def test_build_candle_history_plan_covers_all_symbols_and_backfill_window() -> None:
    plan = build_candle_history_plan(
        native_symbols=["BTCUSDT", "ETHUSDT"],
        observed_at="2026-06-21T04:00:00Z",
        history_backfill_hours=336,
        interval="15m",
        page_limit=100,
    )

    assert {item.native_symbol for item in plan.requests} == {"BTCUSDT", "ETHUSDT"}
    assert len([item for item in plan.requests if item.native_symbol == "BTCUSDT"]) == 14
    assert plan.requests[0].start_time_ms == 1780804800000
    assert plan.requests[-1].end_time_ms == 1782014400000


def test_build_market_snapshot_keeps_ticker_strings_and_spread() -> None:
    ticker_rows = normalize_tickers(
        json.loads((FIXTURE_ROOT / "tickers.json").read_text(encoding="utf-8"))
    )

    snapshot = build_market_snapshot(
        provider_id="bitget",
        observed_at="2026-06-21T04:00:00Z",
        ticker_rows=ticker_rows,
        source_payload_sha256="a" * 64,
    )

    ticker = snapshot.tickers[0]
    assert ticker.native_symbol == "BTCUSDT"
    assert ticker.bid1_price == "90216.3"
    assert ticker.ask1_price == "90216.4"
    assert ticker.spread_bps.startswith("0.01108")


def test_market_snapshot_dump_matches_schema() -> None:
    ticker_rows = normalize_tickers(
        json.loads((FIXTURE_ROOT / "tickers.json").read_text(encoding="utf-8"))
    )
    snapshot = build_market_snapshot(
        provider_id="bitget",
        observed_at="2026-06-21T04:00:00Z",
        ticker_rows=ticker_rows,
        source_payload_sha256="a" * 64,
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_market_snapshot.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(snapshot.model_dump(mode="json"))
