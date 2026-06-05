from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack


def _candidate(candidate_id: str, *, status: str = "candidate") -> TradeCandidate:
    return TradeCandidate(
        schema_version="trade_candidate.v1",
        candidate_id=candidate_id,
        generated_at=datetime.now(timezone.utc),
        signal_id="sig-001",
        strategy_id="equity_index_momentum_v0",
        trial_id="trial-001",
        execution_venue="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        side="long",
        timeframe="4h",
        status=status,
        raw_score=1.2,
        rank_score=0.9,
        percentile_rank=0.9,
        tail_bucket="top",
        confidence=0.8,
        entry_reason_codes=["close_above_sma20"],
        block_reasons=["BLOCK_LOW_SOURCE_CONFIDENCE"] if status == "blocked" else [],
        feature_snapshot_ref="feature-snap-001",
        quote_ref="quote-001",
        tracking_ref="tracking-001",
    )


def test_trade_candidate_is_not_live_order() -> None:
    candidate = _candidate("candidate-001")

    assert candidate.live_order_submitted is False
    assert candidate.execution_symbol == "XYZ100"
    assert candidate.real_market_symbol == "QQQ"


def test_trade_candidate_accepts_bitget_demo_venue() -> None:
    candidate = TradeCandidate(
        **{
            **_candidate("candidate-bitget-001").model_dump(),
            "execution_venue": "bitget_demo",
            "execution_symbol": "BTCUSDT",
            "real_market_symbol": "BTCUSDT",
        }
    )

    assert candidate.execution_venue == "bitget_demo"
    assert candidate.live_order_submitted is False


def test_trade_candidate_rejects_live_order_claim() -> None:
    with pytest.raises(ValidationError, match="live_order_submitted"):
        TradeCandidate(**{**_candidate("candidate-001").model_dump(), "live_order_submitted": True})


def test_paper_candidate_pack_preserves_selected_rejected_and_blocked() -> None:
    pack = PaperCandidatePack(
        schema_version="paper_candidate_pack.v1",
        pack_id="pack-001",
        generated_at=datetime.now(timezone.utc),
        evaluation_plan_id="initial_walkforward",
        data_snapshot_id="data-snap-001",
        feature_snapshot_id="feature-snap-001",
        trial_group_id="group-001",
        candidates=[
            _candidate("candidate-001"),
            _candidate("candidate-002", status="blocked"),
        ],
        selected_candidate_ids=["candidate-001"],
        rejected_candidate_ids=["candidate-002"],
        selection_policy={"rank_score_min": 0.8},
        reason_codes=["selected_top_rank"],
        block_reasons=[],
    )

    assert [candidate.candidate_id for candidate in pack.candidates] == [
        "candidate-001",
        "candidate-002",
    ]
    assert pack.live_order_submitted is False
    assert pack.wallet_used is False
    assert pack.exchange_write_used is False
    assert pack.paper_ready_claimed is False


def test_paper_candidate_pack_rejects_unknown_selected_id() -> None:
    with pytest.raises(ValidationError, match="selected_candidate_ids"):
        PaperCandidatePack(
            schema_version="paper_candidate_pack.v1",
            pack_id="pack-001",
            generated_at=datetime.now(timezone.utc),
            evaluation_plan_id="initial_walkforward",
            data_snapshot_id="data-snap-001",
            feature_snapshot_id="feature-snap-001",
            trial_group_id="group-001",
            candidates=[_candidate("candidate-001")],
            selected_candidate_ids=["missing"],
            rejected_candidate_ids=[],
            selection_policy={},
            reason_codes=[],
            block_reasons=[],
        )


def test_paper_candidate_pack_rejects_duplicate_candidate_ids() -> None:
    with pytest.raises(ValidationError, match="candidate_id values must be unique"):
        PaperCandidatePack(
            schema_version="paper_candidate_pack.v1",
            pack_id="pack-001",
            generated_at=datetime.now(timezone.utc),
            evaluation_plan_id="initial_walkforward",
            data_snapshot_id="data-snap-001",
            feature_snapshot_id="feature-snap-001",
            trial_group_id="group-001",
            candidates=[_candidate("candidate-001"), _candidate("candidate-001")],
            selected_candidate_ids=["candidate-001"],
            rejected_candidate_ids=[],
            selection_policy={},
            reason_codes=[],
            block_reasons=[],
        )


def test_paper_candidate_pack_rejects_duplicate_selected_ids() -> None:
    with pytest.raises(ValidationError, match="selected_candidate_ids must be unique"):
        PaperCandidatePack(
            schema_version="paper_candidate_pack.v1",
            pack_id="pack-001",
            generated_at=datetime.now(timezone.utc),
            evaluation_plan_id="initial_walkforward",
            data_snapshot_id="data-snap-001",
            feature_snapshot_id="feature-snap-001",
            trial_group_id="group-001",
            candidates=[_candidate("candidate-001")],
            selected_candidate_ids=["candidate-001", "candidate-001"],
            rejected_candidate_ids=[],
            selection_policy={},
            reason_codes=[],
            block_reasons=[],
        )
