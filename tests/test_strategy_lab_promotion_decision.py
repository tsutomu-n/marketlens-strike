from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sis.research.strategy_lab.promotion_decision import PromotionDecision


def test_promotion_decision_allows_hold_with_reasons() -> None:
    decision = PromotionDecision(
        schema_version="promotion_decision.v1",
        promotion_id="promotion-001",
        generated_at=datetime.now(timezone.utc),
        source_pack_id="pack-001",
        reviewer="tn",
        from_stage="strategy_lab",
        to_stage="paper_observation",
        decision="hold",
        required_evidence=["trial_ledger", "paper_candidate_pack"],
        observed_evidence=["trial_ledger"],
        approval_reasons=[],
        rejection_reasons=["missing_out_of_sample_window"],
    )

    assert decision.decision == "hold"
    assert decision.live_ready_claimed is False


def test_promotion_decision_rejects_live_ready_claim() -> None:
    with pytest.raises(ValidationError, match="live_ready_claimed"):
        PromotionDecision(
            schema_version="promotion_decision.v1",
            promotion_id="promotion-001",
            generated_at=datetime.now(timezone.utc),
            source_pack_id="pack-001",
            reviewer="tn",
            from_stage="strategy_lab",
            to_stage="paper_observation",
            decision="promote",
            required_evidence=["trial_ledger"],
            observed_evidence=["trial_ledger"],
            approval_reasons=["reviewed"],
            rejection_reasons=[],
            live_ready_claimed=True,
        )


def test_promotion_decision_rejects_paper_ready_claim() -> None:
    with pytest.raises(ValidationError, match="paper_ready_claimed"):
        PromotionDecision(
            schema_version="promotion_decision.v1",
            promotion_id="promotion-001",
            generated_at=datetime.now(timezone.utc),
            source_pack_id="pack-001",
            reviewer="tn",
            from_stage="strategy_lab",
            to_stage="paper_observation",
            decision="hold",
            required_evidence=["trial_ledger"],
            observed_evidence=["trial_ledger"],
            approval_reasons=[],
            rejection_reasons=["still_research"],
            paper_ready_claimed=True,
        )


def test_promotion_decision_promote_requires_observed_evidence() -> None:
    with pytest.raises(ValidationError, match="required_evidence"):
        PromotionDecision(
            schema_version="promotion_decision.v1",
            promotion_id="promotion-001",
            generated_at=datetime.now(timezone.utc),
            source_pack_id="pack-001",
            reviewer="tn",
            from_stage="strategy_lab",
            to_stage="paper_observation",
            decision="promote",
            required_evidence=["trial_ledger", "paper_candidate_pack"],
            observed_evidence=["trial_ledger"],
            approval_reasons=["reviewed"],
            rejection_reasons=[],
        )
