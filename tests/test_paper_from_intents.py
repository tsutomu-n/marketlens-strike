from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import polars as pl

from sis.paper.runner import run_paper_from_intents
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview


def _write_quotes(data_dir, *, venue: str = "trade_xyz", symbol: str = "XYZ100") -> None:
    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    pl.DataFrame(
        [
            {
                "ts_client": now,
                "venue": venue,
                "canonical_symbol": symbol,
                "venue_symbol": symbol,
                "best_bid": 99.9,
                "best_ask": 100.1,
                "bid_price": 99.9,
                "ask_price": 100.1,
                "mark_price": 100.0,
                "mid_price": 100.0,
                "oracle_price": 100.0,
                "index_price": 100.0,
                "spread_bps": 2.0,
                "depth_10bps_usd": 5000.0,
                "funding_rate": 0.0001,
                "source_confidence": 0.95,
                "venue_quality_score": 0.95,
                "trade_allowed": True,
                "fee_mode": "standard",
                "oracle_ts_ms": int(now.timestamp() * 1000),
                "market_status": "open",
                "is_tradable": True,
            }
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")


def _intent(
    valid_until: datetime,
    *,
    venue: str = "trade_xyz",
    symbol: str = "XYZ100",
    real_symbol: str = "QQQ",
) -> PaperIntentPreview:
    now = datetime.now(timezone.utc)
    return PaperIntentPreview(
        schema_version="paper_intent_preview.v1",
        intent_id="intent-001",
        generated_at=now,
        valid_until=valid_until,
        source_pack_id="pack-001",
        candidate_id="candidate-001",
        strategy_id="equity_index_momentum_v0",
        execution_venue=venue,
        execution_symbol=symbol,
        real_market_symbol=real_symbol,
        action="enter",
        side="long",
        order_style="paper_taker",
        price_reference="mark",
        notional_usd=1000.0,
        quantity=1.0,
        source_quote_ts=now,
        source_tracking_ts=now,
        source_feature_ts=now,
        source_phase_gate_run_id="phase-gate-001",
    )


def test_run_paper_from_intents_revalidates_and_writes_paper_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_quotes(data_dir)
    intents_path = data_dir / "bot/paper_intent_preview.json"
    intents_path.parent.mkdir(parents=True)
    intent = _intent(datetime.now(timezone.utc) + timedelta(minutes=15))
    intents_path.write_text(json.dumps([intent.model_dump(mode="json")]), encoding="utf-8")

    summary = run_paper_from_intents(data_dir, intents_path=intents_path)

    assert summary.orders_count == 1
    assert summary.fills_count == 1
    assert summary.blocked_count == 0
    assert summary.orders_path.exists()
    assert summary.fills_path.exists()
    assert summary.observation_ledger_path.exists()
    text = summary.observation_ledger_path.read_text(encoding="utf-8")
    assert '"exchange_write_used": false' in text


def test_run_paper_from_intents_accepts_bitget_demo_fixture_quote(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_quotes(data_dir, venue="bitget_demo", symbol="BTCUSDT")
    intents_path = data_dir / "bot/paper_intent_preview.json"
    intents_path.parent.mkdir(parents=True)
    intent = _intent(
        datetime.now(timezone.utc) + timedelta(minutes=15),
        venue="bitget_demo",
        symbol="BTCUSDT",
        real_symbol="BTCUSDT",
    )
    intents_path.write_text(json.dumps([intent.model_dump(mode="json")]), encoding="utf-8")

    summary = run_paper_from_intents(data_dir, intents_path=intents_path)

    assert summary.orders_count == 1
    assert summary.fills_count == 1
    fills = pl.read_parquet(summary.fills_path)
    assert fills.get_column("venue").to_list() == ["bitget_demo"]
    assert fills.get_column("estimated_round_trip_cost_bps").to_list() == [9.0]
    text = summary.observation_ledger_path.read_text(encoding="utf-8")
    assert '"exchange_write_used": false' in text


def test_run_paper_from_intents_does_not_fallback_across_venues(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_quotes(data_dir, venue="trade_xyz", symbol="BTCUSDT")
    intents_path = data_dir / "bot/paper_intent_preview.json"
    intents_path.parent.mkdir(parents=True)
    intent = _intent(
        datetime.now(timezone.utc) + timedelta(minutes=15),
        venue="bitget_demo",
        symbol="BTCUSDT",
        real_symbol="BTCUSDT",
    )
    intents_path.write_text(json.dumps([intent.model_dump(mode="json")]), encoding="utf-8")

    summary = run_paper_from_intents(data_dir, intents_path=intents_path)

    assert summary.orders_count == 0
    assert summary.fills_count == 0
    assert summary.blocked_count == 1
    assert "LATEST_QUOTE_MISSING" in summary.observation_ledger_path.read_text(encoding="utf-8")


def test_run_paper_from_intents_blocks_expired_intent(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_quotes(data_dir)
    intents_path = data_dir / "bot/paper_intent_preview.json"
    intents_path.parent.mkdir(parents=True)
    intent = _intent(datetime.now(timezone.utc) - timedelta(minutes=1))
    intents_path.write_text(json.dumps([intent.model_dump(mode="json")]), encoding="utf-8")

    summary = run_paper_from_intents(data_dir, intents_path=intents_path)

    assert summary.orders_count == 0
    assert summary.fills_count == 0
    assert summary.blocked_count == 1
    assert "INTENT_EXPIRED" in summary.observation_ledger_path.read_text(encoding="utf-8")
