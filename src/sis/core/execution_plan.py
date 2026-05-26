from __future__ import annotations

from pydantic import BaseModel, Field

from sis.core.context import DecisionContext
from sis.core.decision import RiskDecision, StrategyDecision


class ExecutionPlan(BaseModel):
    action: str
    venue: str
    canonical_symbol: str
    timeframe: str
    price_reference: str | None = None
    source_confidence: float | None = None
    venue_quality_score: float | None = None
    tracking_trade_allowed: bool | None = None
    fee_mode: str | None = None
    estimated_round_trip_cost_bps: float | None = None
    fill_price_source: str | None = None
    notes: list[str] = Field(default_factory=list)


def build_execution_plan(
    context: DecisionContext,
    strategy_decision: StrategyDecision,
    risk_decision: RiskDecision,
    *,
    price_reference: str | None = "mark_or_exec",
) -> ExecutionPlan:
    if not strategy_decision.should_enter:
        return ExecutionPlan(
            action="skip",
            venue=context.venue,
            canonical_symbol=context.canonical_symbol,
            timeframe=context.timeframe,
            price_reference=price_reference,
            notes=[strategy_decision.reason],
        )
    if not risk_decision.allowed:
        return ExecutionPlan(
            action="skip",
            venue=context.venue,
            canonical_symbol=context.canonical_symbol,
            timeframe=context.timeframe,
            price_reference=price_reference,
            notes=risk_decision.blocked_reasons[:],
        )
    action = "enter_long" if strategy_decision.side == "long" else "enter_short"
    return ExecutionPlan(
        action=action,
        venue=context.venue,
        canonical_symbol=context.canonical_symbol,
        timeframe=context.timeframe,
        price_reference=price_reference,
        notes=[strategy_decision.reason],
    )
