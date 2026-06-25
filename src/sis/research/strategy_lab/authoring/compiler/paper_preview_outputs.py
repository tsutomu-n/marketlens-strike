from __future__ import annotations

from datetime import datetime

from sis.research.strategy_lab.authoring.compiler.paper_preview_run_context import (
    _PaperPreviewRunContext,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.promotion_decision import PromotionDecision


def _paper_preview_candidate_pack(
    *,
    spec: StrategyAuthoringSpec,
    context: _PaperPreviewRunContext,
    candidates: list[TradeCandidate],
    selected_candidate_ids: list[str],
    rejected_candidate_ids: list[str],
    rejection_reasons: list[str],
    generated_at: datetime,
) -> PaperCandidatePack:
    return PaperCandidatePack(
        schema_version="paper_candidate_pack.v1",
        pack_id=f"paper-pack-{context.run_id}",
        generated_at=generated_at,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        trial_group_id=context.trial_group_id,
        candidates=candidates,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        selection_policy={
            "source": "strategy_authoring",
            "default_decision": spec.promotion.default_decision,
        },
        reason_codes=["strategy_authoring_v1"],
        block_reasons=[] if context.selected else rejection_reasons,
    )


def _paper_preview_promotion_decision(
    *,
    spec: StrategyAuthoringSpec,
    context: _PaperPreviewRunContext,
    pack: PaperCandidatePack,
    generated_at: datetime,
) -> PromotionDecision:
    return PromotionDecision(
        schema_version="promotion_decision.v1",
        promotion_id=f"promotion-{context.run_id}",
        generated_at=generated_at,
        source_pack_id=pack.pack_id,
        reviewer=None,
        from_stage="strategy_lab",
        to_stage="paper_observation",
        decision=spec.promotion.default_decision,
        required_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        observed_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        approval_reasons=[],
        rejection_reasons=["operator_review_required"],
        scorecard_summary=context.scorecard_summary,
    )
