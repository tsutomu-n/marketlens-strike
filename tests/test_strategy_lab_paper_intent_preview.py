from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview


def _intent(**overrides) -> PaperIntentPreview:
    payload = {
        "schema_version": "paper_intent_preview.v1",
        "intent_id": "intent-001",
        "generated_at": datetime.now(timezone.utc),
        "valid_until": datetime.now(timezone.utc) + timedelta(minutes=15),
        "source_pack_id": "pack-001",
        "candidate_id": "candidate-001",
        "strategy_id": "equity_index_momentum_v0",
        "execution_venue": "trade_xyz",
        "execution_symbol": "XYZ100",
        "real_market_symbol": "QQQ",
        "action": "enter",
        "side": "long",
        "order_style": "paper_taker",
        "price_reference": "mark",
        "notional_usd": 1000.0,
        "quantity": None,
        "source_quote_ts": datetime.now(timezone.utc),
        "source_tracking_ts": datetime.now(timezone.utc),
        "source_feature_ts": datetime.now(timezone.utc),
        "source_phase_gate_run_id": "phase-gate-001",
    }
    payload.update(overrides)
    return PaperIntentPreview(**payload)


def test_paper_intent_preview_is_paper_only_and_requires_revalidation() -> None:
    intent = _intent()

    assert intent.requires_revalidation is True
    assert intent.paper_only is True
    assert intent.live_conversion_allowed is False
    assert intent.live_order_submitted is False
    assert intent.wallet_used is False
    assert intent.exchange_write_used is False


def test_paper_intent_preview_accepts_bitget_demo_venue() -> None:
    intent = _intent(
        execution_venue="bitget_demo",
        execution_symbol="BTCUSDT",
        real_market_symbol="BTCUSDT",
    )

    assert intent.execution_venue == "bitget_demo"
    assert intent.paper_only is True
    assert intent.exchange_write_used is False


def test_paper_intent_preview_rejects_live_conversion() -> None:
    with pytest.raises(ValidationError, match="live_conversion_allowed"):
        _intent(live_conversion_allowed=True)


def test_paper_intent_preview_rejects_missing_revalidation() -> None:
    with pytest.raises(ValidationError, match="requires_revalidation"):
        _intent(requires_revalidation=False)
