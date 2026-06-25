from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.portfolio_allocation_weights import (
    _allocation_raw_weights as _allocation_raw_weights,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_limit_resolution import (
    _portfolio_timestamp_limit,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_neutral_allocation import (
    _neutral_allocated_rows as _neutral_allocated_rows,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_allocation(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.allocation_method == "none":
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
        target = _portfolio_target_total_position_weight(timestamp_rows, portfolio)
        if target is None:
            selected.extend(timestamp_rows)
            continue
        if portfolio.allocation_method in {
            "dollar_neutral",
            "beta_neutral",
            "group_neutral",
        }:
            selected.extend(
                _neutral_allocated_rows(
                    timestamp_rows,
                    target=target,
                    method=portfolio.allocation_method,
                )
            )
            continue
        raw_weights = _allocation_raw_weights(timestamp_rows, portfolio)
        total_raw = sum(raw_weights)
        for row, raw_weight in zip(timestamp_rows, raw_weights, strict=True):
            allocated = 0.0 if total_raw == 0.0 else target * raw_weight / total_raw
            updated = dict(row)
            updated["position_weight"] = allocated
            selected.append(updated)
    return selected


def _portfolio_target_total_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    column = portfolio.target_total_position_weight_column
    if column is None:
        return portfolio.target_total_position_weight
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.target_total_position_weight,
        value_key="_portfolio_target_total_position_weight",
        field_name="rules.portfolio.target_total_position_weight_column",
    )
