from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TradeCandidate(BaseModel):
    schema_version: Literal["trade_candidate.v1"]
    candidate_id: str
    generated_at: datetime
    signal_id: str | None
    strategy_id: str
    trial_id: str | None
    execution_venue: Literal["trade_xyz"]
    execution_symbol: str
    real_market_symbol: str
    side: Literal["long", "short", "none"]
    timeframe: str
    status: Literal["candidate", "blocked", "no_signal", "hold"]
    raw_score: float | None
    rank_score: float | None
    percentile_rank: float | None
    tail_bucket: Literal["top", "middle", "bottom", "none"]
    confidence: float
    unique_contribution_score: float | None = None
    index_exposure_score: float | None = None
    entry_reason_codes: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    feature_snapshot_ref: str | None
    quote_ref: str | None
    tracking_ref: str | None
    live_order_submitted: bool = False

    @model_validator(mode="after")
    def validate_candidate(self) -> TradeCandidate:
        for field_name in ("candidate_id", "strategy_id", "execution_symbol", "real_market_symbol"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.live_order_submitted:
            raise ValueError("live_order_submitted must remain false for TradeCandidate")
        if self.rank_score is not None and not 0.0 <= self.rank_score <= 1.0:
            raise ValueError("rank_score must be between 0 and 1")
        if self.percentile_rank is not None and not 0.0 <= self.percentile_rank <= 1.0:
            raise ValueError("percentile_rank must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        self.execution_symbol = self.execution_symbol.strip().upper()
        self.real_market_symbol = self.real_market_symbol.strip().upper()
        return self
