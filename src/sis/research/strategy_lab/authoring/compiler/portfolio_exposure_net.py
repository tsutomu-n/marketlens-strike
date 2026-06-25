from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.portfolio_net_exposure_selection import (
    _first_over_limit_group_net_weight,
    _lowest_rank_overweight_candidate,
    _net_position_weight,
    _overweight_side,
)
from sis.research.strategy_lab.authoring.compiler.trade_blocking import _block_trade_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        net_weight = _net_position_weight(accepted)
        if abs(net_weight) <= max_abs_net_position_weight:
            return accepted, blocked

        candidate = _lowest_rank_overweight_candidate(accepted, side=_overweight_side(net_weight))
        if candidate is None:
            return accepted, blocked

        remove_index, row = candidate
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_net_exposure_limit")
        )
        accepted.pop(remove_index)


def _apply_portfolio_group_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_group_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_group_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        over_limit = _first_over_limit_group_net_weight(accepted, max_group_abs_net_position_weight)
        if over_limit is None:
            return accepted, blocked

        group, net_weight = over_limit
        candidate = _lowest_rank_overweight_candidate(
            accepted,
            side=_overweight_side(net_weight),
            group=group,
        )
        if candidate is None:
            return accepted, blocked

        remove_index, row = candidate
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_group_net_exposure_limit")
        )
        accepted.pop(remove_index)
