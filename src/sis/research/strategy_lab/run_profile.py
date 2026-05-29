from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

DEFAULT_FORBIDDEN_CLAIMS = [
    "profitability_claim",
    "paper_ready_claim",
    "tiny_live_ready_claim",
    "live_ready_claim",
]


class StrategyRunProfile(BaseModel):
    profile_id: str = "strategy_lab"
    strategy_lab: bool = True
    exchange_write_allowed: bool = False
    wallet_required: bool = False
    live_order_submission_allowed: bool = False
    run_mode: Literal["strategy_lab", "walkforward_research", "paper_candidate"] = "strategy_lab"
    forbidden_claims: list[str] = Field(default_factory=lambda: DEFAULT_FORBIDDEN_CLAIMS[:])

    @model_validator(mode="after")
    def reject_live_surfaces(self) -> StrategyRunProfile:
        if not self.strategy_lab:
            return self
        if self.exchange_write_allowed:
            raise ValueError("exchange_write_allowed must be false for strategy_lab")
        if self.wallet_required:
            raise ValueError("wallet_required must be false for strategy_lab")
        if self.live_order_submission_allowed:
            raise ValueError("live_order_submission_allowed must be false for strategy_lab")
        missing = set(DEFAULT_FORBIDDEN_CLAIMS).difference(self.forbidden_claims)
        if missing:
            raise ValueError(f"strategy_lab forbidden_claims missing: {sorted(missing)}")
        return self

    def ensure_claim_allowed(self, claim: str) -> None:
        if claim in self.forbidden_claims:
            raise ValueError(f"{claim} is forbidden for strategy_lab")
