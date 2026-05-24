from __future__ import annotations

from typing import Any

from sis.core.decision import DecisionRecord
from sis.core.execution_plan import ExecutionPlan
from sis.paper.fills import PaperFill


def _price_for_action(action: str, row: dict[str, Any]) -> float | None:
    if action == "enter_long":
        for key in ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    if action == "enter_short":
        for key in ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    if action == "exit_long":
        for key in ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    if action == "exit_short":
        for key in ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    return None


class PaperBroker:
    def create_fill(
        self,
        execution_plan: ExecutionPlan,
        decision_record: DecisionRecord,
        quote_row: dict[str, Any],
        *,
        quantity: float = 1.0,
    ) -> PaperFill | None:
        if execution_plan.action == "skip":
            return None
        price = _price_for_action(execution_plan.action, quote_row)
        if price is None:
            return None
        return PaperFill(
            ts_fill=decision_record.context.quote_ts,
            venue=execution_plan.venue,
            canonical_symbol=execution_plan.canonical_symbol,
            side=decision_record.strategy_decision.side,
            action=execution_plan.action,
            quantity=quantity,
            price=price,
            strategy_name=decision_record.strategy_decision.strategy_name,
            notes=execution_plan.notes[:],
        )
