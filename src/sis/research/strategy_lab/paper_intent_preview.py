from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from sis.venues.ids import VenueId
from sis.venues.suitability import venue_suitability_block_reasons


class PaperIntentPreview(BaseModel):
    schema_version: Literal["paper_intent_preview.v1"]
    intent_id: str
    generated_at: datetime
    valid_until: datetime | None
    source_pack_id: str
    candidate_id: str
    strategy_id: str
    execution_venue: VenueId
    execution_symbol: str
    real_market_symbol: str
    action: Literal["enter", "exit", "reduce", "skip"]
    side: Literal["long", "short", "none"]
    order_style: Literal["paper_taker", "paper_maker", "skip"]
    price_reference: Literal["best_bid", "best_ask", "mid", "mark", "oracle"]
    notional_usd: float | None
    quantity: float | None
    source_quote_ts: datetime | None
    source_tracking_ts: datetime | None
    source_feature_ts: datetime | None
    source_phase_gate_run_id: str | None
    scorecard_summary: dict[str, Any] = Field(default_factory=dict)
    requires_revalidation: bool = True
    paper_only: bool = True
    live_conversion_allowed: bool = False
    live_order_submitted: bool = False
    wallet_used: bool = False
    exchange_write_used: bool = False
    operator_promotion_path: str | None = None
    operator_promotion_hash: str | None = None

    @model_validator(mode="after")
    def validate_preview(self) -> PaperIntentPreview:
        for field_name in (
            "intent_id",
            "source_pack_id",
            "candidate_id",
            "strategy_id",
            "execution_symbol",
            "real_market_symbol",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if not self.requires_revalidation:
            raise ValueError("requires_revalidation must be true for PaperIntentPreview")
        if not self.paper_only:
            raise ValueError("paper_only must be true for PaperIntentPreview")
        if self.live_conversion_allowed:
            raise ValueError("live_conversion_allowed must remain false for PaperIntentPreview")
        if self.live_order_submitted:
            raise ValueError("live_order_submitted must remain false for PaperIntentPreview")
        if self.wallet_used:
            raise ValueError("wallet_used must remain false for PaperIntentPreview")
        if self.exchange_write_used:
            raise ValueError("exchange_write_used must remain false for PaperIntentPreview")
        self.execution_symbol = self.execution_symbol.strip().upper()
        self.real_market_symbol = self.real_market_symbol.strip().upper()
        block_reasons = venue_suitability_block_reasons(
            venue_id=str(self.execution_venue),
            execution_symbol=self.execution_symbol,
            real_market_symbol=self.real_market_symbol,
            stage="paper_intent",
            operator_promotion_evidence={
                "operator_promotion_path": self.operator_promotion_path,
                "operator_promotion_hash": self.operator_promotion_hash,
            },
        )
        if block_reasons:
            raise ValueError(f"PaperIntentPreview venue unsuitable: {block_reasons}")
        return self
