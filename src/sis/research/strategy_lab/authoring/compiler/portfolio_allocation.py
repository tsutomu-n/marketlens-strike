from __future__ import annotations

from typing import Any, Iterable

from sis.research.strategy_lab.authoring.compiler.common import _position_weight_value
from sis.research.strategy_lab.authoring.compiler.portfolio_limit_resolution import (
    _portfolio_timestamp_limit,
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


def _neutral_allocated_rows(
    rows: list[dict[str, Any]], *, target: float, method: str
) -> list[dict[str, Any]]:
    if method == "group_neutral":
        group_rows: dict[str, list[dict[str, Any]]] = {}
        ungrouped: list[dict[str, Any]] = []
        for row in rows:
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_rows.setdefault(group, []).append(row)
            else:
                ungrouped.append(row)
        group_target = target / len(group_rows) if group_rows else 0.0
        allocated: list[dict[str, Any]] = []
        for grouped_rows in group_rows.values():
            allocated.extend(
                _side_neutral_allocated_rows(
                    grouped_rows,
                    long_target=group_target / 2.0,
                    short_target=group_target / 2.0,
                )
            )
        allocated.extend(_side_neutral_allocated_rows(ungrouped, long_target=0.0, short_target=0.0))
        return allocated

    long_target = target / 2.0
    short_target = target / 2.0
    if method == "beta_neutral":
        long_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "long")
        short_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "short")
        if long_beta > 0.0 and short_beta > 0.0:
            long_target = target * short_beta / (long_beta + short_beta)
            short_target = target * long_beta / (long_beta + short_beta)
    return _side_neutral_allocated_rows(rows, long_target=long_target, short_target=short_target)


def _weighted_average_abs_beta(rows: Iterable[dict[str, Any]]) -> float:
    weighted_beta = 0.0
    total_weight = 0.0
    for row in rows:
        beta = row.get("_allocation_beta")
        if not isinstance(beta, int | float):
            continue
        weight = abs(_position_weight_value(row))
        weighted_beta += abs(float(beta)) * weight
        total_weight += weight
    return 0.0 if total_weight == 0.0 else weighted_beta / total_weight


def _side_neutral_allocated_rows(
    rows: list[dict[str, Any]], *, long_target: float, short_target: float
) -> list[dict[str, Any]]:
    by_side = {
        "long": [row for row in rows if row.get("side") == "long"],
        "short": [row for row in rows if row.get("side") == "short"],
    }
    allocated: list[dict[str, Any]] = []
    for side, side_rows in by_side.items():
        side_target = long_target if side == "long" else short_target
        total_raw = sum(abs(_position_weight_value(row)) for row in side_rows)
        for row in side_rows:
            updated = dict(row)
            updated["position_weight"] = (
                0.0
                if total_raw == 0.0
                else side_target * abs(_position_weight_value(row)) / total_raw
            )
            allocated.append(updated)
    return allocated
