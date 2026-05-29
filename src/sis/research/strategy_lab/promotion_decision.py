from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PromotionDecision(BaseModel):
    schema_version: Literal["promotion_decision.v1"]
    promotion_id: str
    generated_at: datetime
    source_pack_id: str
    reviewer: str | None
    from_stage: Literal["strategy_lab", "paper_candidate"]
    to_stage: Literal["paper_observation", "micro_live_candidate"]
    decision: Literal["promote", "reject", "hold"]
    required_evidence: list[str]
    observed_evidence: list[str]
    approval_reasons: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    paper_ready_claimed: bool = False
    tiny_live_ready_claimed: bool = False
    live_ready_claimed: bool = False
    wallet_used: bool = False
    exchange_write_used: bool = False

    @model_validator(mode="after")
    def validate_decision(self) -> PromotionDecision:
        for field_name in ("promotion_id", "source_pack_id"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.paper_ready_claimed:
            raise ValueError("paper_ready_claimed must remain false for PromotionDecision")
        if self.tiny_live_ready_claimed:
            raise ValueError("tiny_live_ready_claimed must remain false for PromotionDecision")
        if self.live_ready_claimed:
            raise ValueError("live_ready_claimed must remain false for PromotionDecision")
        if self.wallet_used:
            raise ValueError("wallet_used must remain false for PromotionDecision")
        if self.exchange_write_used:
            raise ValueError("exchange_write_used must remain false for PromotionDecision")
        if self.decision == "promote":
            missing = set(self.required_evidence).difference(self.observed_evidence)
            if missing:
                raise ValueError(
                    f"required_evidence missing from observed_evidence: {sorted(missing)}"
                )
            if not self.approval_reasons:
                raise ValueError("approval_reasons required for promote")
        if self.decision in {"reject", "hold"} and not self.rejection_reasons:
            raise ValueError("rejection_reasons required for reject/hold")
        return self
