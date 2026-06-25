from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import _position_weight_value
from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules


@dataclass(frozen=True)
class _PortfolioExposureState:
    total_weight: float = 0.0
    long_weight: float = 0.0
    short_weight: float = 0.0
    symbol_weights: dict[str, float] = field(default_factory=dict)
    group_weights: dict[str, float] = field(default_factory=dict)


def _portfolio_exposure_block_reason(
    row: dict[str, Any],
    *,
    portfolio: PortfolioRules,
    max_total_position_weight: float | None,
    max_long_position_weight: float | None,
    max_short_position_weight: float | None,
    max_symbol_position_weight: float | None,
    max_group_position_weight: float | None,
    state: _PortfolioExposureState,
) -> str | None:
    weight = abs(_position_weight_value(row))
    side = str(row.get("side") or "")
    symbol = str(row.get("execution_symbol") or "")
    group = str(row.get("_portfolio_group") or "").strip()
    if (
        max_total_position_weight is not None
        and state.total_weight + weight > max_total_position_weight
    ):
        return "portfolio_total_exposure_limit"
    if side == "long" and max_long_position_weight is not None:
        if state.long_weight + weight > max_long_position_weight:
            return "portfolio_long_exposure_limit"
    if side == "short" and max_short_position_weight is not None:
        if state.short_weight + weight > max_short_position_weight:
            return "portfolio_short_exposure_limit"
    if max_symbol_position_weight is not None:
        if state.symbol_weights.get(symbol, 0.0) + weight > max_symbol_position_weight:
            return "portfolio_symbol_exposure_limit"
    if (
        max_group_position_weight is not None
        or portfolio.max_group_abs_net_position_weight is not None
        or portfolio.max_group_abs_net_position_weight_column is not None
    ):
        if not group:
            return "portfolio_group_missing"
    if max_group_position_weight is not None:
        if state.group_weights.get(group, 0.0) + weight > max_group_position_weight:
            return "portfolio_group_exposure_limit"
    return None


def _accepted_portfolio_exposure_state(
    state: _PortfolioExposureState, row: dict[str, Any]
) -> _PortfolioExposureState:
    weight = abs(_position_weight_value(row))
    side = str(row.get("side") or "")
    symbol = str(row.get("execution_symbol") or "")
    group = str(row.get("_portfolio_group") or "").strip()
    symbol_weights = {**state.symbol_weights}
    symbol_weights[symbol] = symbol_weights.get(symbol, 0.0) + weight
    group_weights = {**state.group_weights}
    if group:
        group_weights[group] = group_weights.get(group, 0.0) + weight
    return _PortfolioExposureState(
        total_weight=state.total_weight + weight,
        long_weight=state.long_weight + (weight if side == "long" else 0.0),
        short_weight=state.short_weight + (weight if side == "short" else 0.0),
        symbol_weights=symbol_weights,
        group_weights=group_weights,
    )
