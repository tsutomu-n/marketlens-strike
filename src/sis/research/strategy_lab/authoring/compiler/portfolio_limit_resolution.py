from __future__ import annotations

import math
from typing import Any

from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules


def _portfolio_timestamp_limit(
    rows: list[dict[str, Any]],
    *,
    fixed: float | None,
    value_key: str,
    field_name: str,
) -> float | None:
    resolved: list[float] = []
    for row in rows:
        raw_value = row.get(value_key)
        value = float(raw_value) if isinstance(raw_value, int | float) else None
        if value is None:
            continue
        if value < 0:
            raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
        resolved.append(value)
    if not resolved:
        return fixed
    first = resolved[0]
    if any(not math.isclose(value, first, rel_tol=0.0, abs_tol=1e-12) for value in resolved[1:]):
        raise StrategyAuthoringValidationError(
            f"{field_name} must resolve to one value per timestamp"
        )
    return first


def _portfolio_max_total_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_total_position_weight,
        value_key="_portfolio_max_total_position_weight",
        field_name="rules.portfolio.max_total_position_weight_column",
    )


def _portfolio_max_long_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_long_position_weight,
        value_key="_portfolio_max_long_position_weight",
        field_name="rules.portfolio.max_long_position_weight_column",
    )


def _portfolio_max_short_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_short_position_weight,
        value_key="_portfolio_max_short_position_weight",
        field_name="rules.portfolio.max_short_position_weight_column",
    )


def _portfolio_max_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_abs_net_position_weight,
        value_key="_portfolio_max_abs_net_position_weight",
        field_name="rules.portfolio.max_abs_net_position_weight_column",
    )


def _portfolio_max_symbol_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_symbol_position_weight,
        value_key="_portfolio_max_symbol_position_weight",
        field_name="rules.portfolio.max_symbol_position_weight_column",
    )


def _portfolio_max_group_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_group_position_weight,
        value_key="_portfolio_max_group_position_weight",
        field_name="rules.portfolio.max_group_position_weight_column",
    )


def _portfolio_max_group_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_group_abs_net_position_weight,
        value_key="_portfolio_max_group_abs_net_position_weight",
        field_name="rules.portfolio.max_group_abs_net_position_weight_column",
    )
