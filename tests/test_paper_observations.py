from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from sis.paper.fills import PaperFill
from sis.paper.observations import paper_observation_payload, quote_age_ms, write_observation
from sis.paper.orders import PaperOrder
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview


def _intent(*, notional_usd: float | None = 1000.0) -> PaperIntentPreview:
    now = datetime(2026, 6, 26, 6, 0, tzinfo=timezone.utc)
    return PaperIntentPreview(
        schema_version="paper_intent_preview.v1",
        intent_id="intent-001",
        generated_at=now,
        valid_until=now + timedelta(minutes=15),
        source_pack_id="pack-001",
        candidate_id="candidate-001",
        strategy_id="equity_index_momentum_v0",
        execution_venue="trade_xyz",
        execution_symbol="SP500",
        real_market_symbol="SPY",
        action="enter",
        side="long",
        order_style="paper_taker",
        price_reference="mark",
        notional_usd=notional_usd,
        quantity=2.0,
        source_quote_ts=now,
        source_tracking_ts=now,
        source_feature_ts=now,
        source_phase_gate_run_id="phase-gate-001",
        operator_promotion_path="data/research/ndx/operator_promotion_decision.json",
        operator_promotion_hash="sha256:abc",
    )


def test_quote_age_ms_returns_elapsed_milliseconds_or_none() -> None:
    now = datetime(2026, 6, 26, 6, 0, 1, 250000, tzinfo=timezone.utc)

    assert quote_age_ms(now, datetime(2026, 6, 26, 6, 0, tzinfo=timezone.utc)) == 1250
    assert quote_age_ms(now, None) is None


def test_paper_observation_payload_preserves_quote_fill_and_safety_fields() -> None:
    now = datetime(2026, 6, 26, 6, 0, 1, tzinfo=timezone.utc)
    quote_ts = datetime(2026, 6, 26, 6, 0, tzinfo=timezone.utc)
    intent = _intent(notional_usd=None)
    order = PaperOrder(
        order_id="order-001",
        ts_order=now,
        venue="trade_xyz",
        canonical_symbol="SP500",
        side="long",
        action="enter_long",
        quantity=2.0,
        strategy_name="equity_index_momentum_v0",
    )
    fill = PaperFill(
        fill_id="fill-001",
        ts_fill=now,
        venue="trade_xyz",
        canonical_symbol="SP500",
        side="long",
        action="enter_long",
        quantity=2.0,
        price=101.5,
        strategy_name="equity_index_momentum_v0",
    )

    payload = paper_observation_payload(
        intent=intent,
        status="paper_filled",
        now=now,
        block_reasons=[],
        quote={
            "market_status": "open",
            "is_tradable": True,
            "spread_bps": 2.5,
            "source_confidence": 0.95,
            "venue_quality_score": 0.9,
        },
        quote_ts=quote_ts,
        order=order,
        fill=fill,
    )

    assert payload == {
        "created_at": "2026-06-26T06:00:01+00:00",
        "intent_id": "intent-001",
        "candidate_id": "candidate-001",
        "venue": "trade_xyz",
        "execution_symbol": "SP500",
        "real_market_symbol": "SPY",
        "status": "paper_filled",
        "block_reasons": [],
        "quote_ts": "2026-06-26T06:00:00+00:00",
        "quote_age_ms": 1000,
        "market_status": "open",
        "is_tradable": True,
        "spread_bps": 2.5,
        "source_confidence": 0.95,
        "venue_quality_score": 0.9,
        "notional_usd": 203.0,
        "quantity": 2.0,
        "order_id": "order-001",
        "fill_id": "fill-001",
        "source_operator_promotion_path": "data/research/ndx/operator_promotion_decision.json",
        "source_operator_promotion_hash": "sha256:abc",
        "live_order_submitted": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "venue_write_used": False,
    }


def test_paper_observation_payload_handles_missing_quote() -> None:
    now = datetime(2026, 6, 26, 6, 0, tzinfo=timezone.utc)

    payload = paper_observation_payload(
        intent=_intent(),
        status="blocked",
        now=now,
        block_reasons=["LATEST_QUOTE_MISSING"],
    )

    assert payload["quote_ts"] is None
    assert payload["quote_age_ms"] is None
    assert payload["market_status"] is None
    assert payload["is_tradable"] is None
    assert payload["spread_bps"] is None
    assert payload["notional_usd"] == 1000.0
    assert payload["order_id"] is None
    assert payload["fill_id"] is None


def test_write_observation_appends_json_lines(tmp_path) -> None:
    path = tmp_path / "paper/observations.jsonl"

    write_observation(path, {"created_at": datetime(2026, 6, 26, tzinfo=timezone.utc), "n": 1})
    write_observation(path, {"n": 2})

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"created_at": "2026-06-26 00:00:00+00:00", "n": 1}, {"n": 2}]
