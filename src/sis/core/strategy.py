from __future__ import annotations

from typing import Protocol

from sis.core.context import DecisionContext
from sis.core.decision import StrategyDecision


class Strategy(Protocol):
    def evaluate(self, context: DecisionContext) -> StrategyDecision: ...


class ResearchSignalStrategy:
    def evaluate(self, context: DecisionContext) -> StrategyDecision:
        side = context.signal_side or "long"
        return StrategyDecision(
            strategy_name=context.strategy_name or "research_signal_strategy",
            should_enter=True,
            side=side,
            timeframe=context.timeframe,
            reason="research_signal_entry",
            score=context.signal_strength,
        )
