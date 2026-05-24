from __future__ import annotations

from pydantic import BaseModel, Field

from sis.core.context import DecisionContext


class StrategyDecision(BaseModel):
    strategy_name: str
    should_enter: bool
    side: str
    timeframe: str
    reason: str
    score: float | None = None
    source: str = "research_signal"


class RiskDecision(BaseModel):
    allowed: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    stale_rejected: bool = False
    halt_rejected: bool = False


class DecisionRecord(BaseModel):
    context: DecisionContext
    strategy_decision: StrategyDecision
    risk_decision: RiskDecision
    execution_plan: dict
