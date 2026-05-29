from __future__ import annotations

from sis.research.strategy_lab.specs import StrategySignalRecord


def summarize_strategy_signals(signals: list[StrategySignalRecord]) -> dict[str, int]:
    blocked = sum(1 for signal in signals if signal.block_reasons)
    return {
        "signal_count": len(signals),
        "blocked_count": blocked,
        "candidate_count": len(signals) - blocked,
    }
