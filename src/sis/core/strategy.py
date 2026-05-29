from __future__ import annotations

from typing import Protocol

from sis.core.context import DecisionContext
from sis.core.decision import StrategyDecision


class Strategy(Protocol):
    def evaluate(self, context: DecisionContext) -> StrategyDecision: ...


class SignalPassthroughStrategy:
    def evaluate(self, context: DecisionContext) -> StrategyDecision:
        side = context.signal_side or "long"
        return StrategyDecision(
            strategy_name=context.strategy_name or "signal_passthrough_strategy",
            should_enter=True,
            side=side,
            timeframe=context.timeframe,
            reason="signal_passthrough_entry",
            score=context.signal_strength,
        )


ResearchSignalStrategy = SignalPassthroughStrategy
