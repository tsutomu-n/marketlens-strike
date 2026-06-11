from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.candidates import TradeCandidate
from sis.venues.suitability import venue_suitability_block_reasons


class PaperCandidatePack(BaseModel):
    schema_version: Literal["paper_candidate_pack.v1"]
    pack_id: str
    generated_at: datetime
    evaluation_plan_id: str
    data_snapshot_id: str
    feature_snapshot_id: str | None
    trial_group_id: str | None
    candidates: list[TradeCandidate]
    selected_candidate_ids: list[str] = Field(default_factory=list)
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    selection_policy: dict[str, Any]
    reason_codes: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    profitability_claimed: bool = False
    paper_ready_claimed: bool = False
    tiny_live_ready_claimed: bool = False
    live_ready_claimed: bool = False
    live_order_submitted: bool = False
    wallet_used: bool = False
    exchange_write_used: bool = False
    operator_promotion_path: str | None = None
    operator_promotion_hash: str | None = None

    @model_validator(mode="after")
    def validate_pack(self) -> PaperCandidatePack:
        for field_name in ("pack_id", "evaluation_plan_id", "data_snapshot_id"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        candidate_id_values = [candidate.candidate_id for candidate in self.candidates]
        candidate_ids = set(candidate_id_values)
        if len(candidate_id_values) != len(candidate_ids):
            raise ValueError("candidate_id values must be unique")
        if len(self.selected_candidate_ids) != len(set(self.selected_candidate_ids)):
            raise ValueError("selected_candidate_ids must be unique")
        if len(self.rejected_candidate_ids) != len(set(self.rejected_candidate_ids)):
            raise ValueError("rejected_candidate_ids must be unique")
        selected_rejected_overlap = set(self.selected_candidate_ids).intersection(
            self.rejected_candidate_ids
        )
        if selected_rejected_overlap:
            raise ValueError(
                f"selected_candidate_ids overlap rejected_candidate_ids: "
                f"{sorted(selected_rejected_overlap)}"
            )
        unknown_selected = set(self.selected_candidate_ids).difference(candidate_ids)
        if unknown_selected:
            raise ValueError(f"selected_candidate_ids unknown: {sorted(unknown_selected)}")
        unknown_rejected = set(self.rejected_candidate_ids).difference(candidate_ids)
        if unknown_rejected:
            raise ValueError(f"rejected_candidate_ids unknown: {sorted(unknown_rejected)}")
        candidates_by_id = {candidate.candidate_id: candidate for candidate in self.candidates}
        invalid_selected = {
            candidate_id: {
                "status": candidates_by_id[candidate_id].status,
                "block_reasons": candidates_by_id[candidate_id].block_reasons,
            }
            for candidate_id in self.selected_candidate_ids
            if candidates_by_id[candidate_id].status != "candidate"
            or candidates_by_id[candidate_id].block_reasons
        }
        if invalid_selected:
            raise ValueError(
                f"selected_candidate_ids contain non-candidate candidates: {invalid_selected}"
            )
        unsuitable_selected = {
            candidate_id: block_reasons
            for candidate_id in self.selected_candidate_ids
            if (
                block_reasons := venue_suitability_block_reasons(
                    venue_id=str(candidates_by_id[candidate_id].execution_venue),
                    execution_symbol=candidates_by_id[candidate_id].execution_symbol,
                    real_market_symbol=candidates_by_id[candidate_id].real_market_symbol,
                    stage="paper_candidate",
                    operator_promotion_evidence={
                        "operator_promotion_path": self.operator_promotion_path,
                        "operator_promotion_hash": self.operator_promotion_hash,
                    },
                )
            )
        }
        if unsuitable_selected:
            raise ValueError(
                f"selected_candidate_ids contain venue-unsuitable candidates: {unsuitable_selected}"
            )
        if self.profitability_claimed:
            raise ValueError("profitability_claimed must remain false for PaperCandidatePack")
        if self.paper_ready_claimed:
            raise ValueError("paper_ready_claimed must remain false for PaperCandidatePack")
        if self.tiny_live_ready_claimed:
            raise ValueError("tiny_live_ready_claimed must remain false for PaperCandidatePack")
        if self.live_ready_claimed:
            raise ValueError("live_ready_claimed must remain false for PaperCandidatePack")
        if self.live_order_submitted:
            raise ValueError("live_order_submitted must remain false for PaperCandidatePack")
        if self.wallet_used:
            raise ValueError("wallet_used must remain false for PaperCandidatePack")
        if self.exchange_write_used:
            raise ValueError("exchange_write_used must remain false for PaperCandidatePack")
        return self
