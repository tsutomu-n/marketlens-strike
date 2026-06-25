from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules


def _allocation_raw_weights(rows: list[dict[str, Any]], portfolio: PortfolioRules) -> list[float]:
    if portfolio.allocation_method == "equal_weight":
        return [1.0 for _row in rows]
    if portfolio.allocation_method == "score_proportional":
        raw_weights = [
            max(0.0, float(row["raw_score"]))
            if isinstance(row.get("raw_score"), int | float)
            else 0.0
            for row in rows
        ]
        return (
            raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]
        )
    raw_weights = [
        1.0 / float(row["_allocation_volatility"])
        if isinstance(row.get("_allocation_volatility"), int | float)
        and float(row["_allocation_volatility"]) > 0.0
        else 0.0
        for row in rows
    ]
    return raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]
