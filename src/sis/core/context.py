from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DecisionContext(BaseModel):
    decision_ts: datetime
    venue: str
    canonical_symbol: str
    timeframe: str
    quote_ts: datetime
    signal_ts: datetime | None = None
    signal_side: str | None = None
    signal_strength: float | None = None
    strategy_name: str | None = None
    market_status: str
    is_tradable: bool
    notes: list[str] = Field(default_factory=list)
