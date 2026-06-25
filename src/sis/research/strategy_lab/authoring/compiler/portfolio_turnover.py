from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _portfolio_turnover_weight_value,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_turnover_budget(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.max_turnover_weight_per_timestamp is None:
        return rows

    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        used_turnover = 0.0
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            turnover_weight = _portfolio_turnover_weight_value(row)
            if used_turnover + turnover_weight > portfolio.max_turnover_weight_per_timestamp:
                blocked_rows.append(
                    _block_trade_row(row, spec=spec, block_reason="portfolio_turnover_budget_limit")
                )
                continue
            used_turnover += turnover_weight
            accepted_rows.append(row)
        selected.extend([*blocked_rows, *accepted_rows])
    return selected
