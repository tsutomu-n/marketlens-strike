from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.portfolio_timestamp_limits import (
    _PORTFOLIO_LIMIT_SPECS,
    _portfolio_limit_value,
    _portfolio_timestamp_limit as _portfolio_timestamp_limit,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules


def _portfolio_limit(
    rows: list[dict[str, Any]], portfolio: PortfolioRules, key: str
) -> float | None:
    return _portfolio_limit_value(rows, portfolio=portfolio, spec=_PORTFOLIO_LIMIT_SPECS[key])


def _portfolio_max_total_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_limit(rows, portfolio, "max_total_position_weight")


def _portfolio_max_long_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_limit(rows, portfolio, "max_long_position_weight")


def _portfolio_max_short_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_limit(rows, portfolio, "max_short_position_weight")


def _portfolio_max_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_limit(rows, portfolio, "max_abs_net_position_weight")


def _portfolio_max_symbol_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_limit(rows, portfolio, "max_symbol_position_weight")


def _portfolio_max_group_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_limit(rows, portfolio, "max_group_position_weight")


def _portfolio_max_group_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_limit(rows, portfolio, "max_group_abs_net_position_weight")
