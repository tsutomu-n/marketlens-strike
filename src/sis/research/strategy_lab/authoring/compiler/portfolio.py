from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.portfolio_allocation import (
    _apply_portfolio_allocation as _apply_portfolio_allocation_impl,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_limits import (
    _apply_portfolio_exposure_limits as _apply_portfolio_exposure_limits_impl,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_net import (
    _apply_portfolio_group_net_exposure_limit as _apply_portfolio_group_net_exposure_limit_impl,
    _apply_portfolio_net_exposure_limit as _apply_portfolio_net_exposure_limit_impl,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_turnover import (
    _apply_portfolio_turnover_budget as _apply_portfolio_turnover_budget_impl,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_signal_limit import (
    _apply_portfolio_signal_limit as _apply_portfolio_signal_limit_impl,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_allocation(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    return _apply_portfolio_allocation_impl(rows, spec)


def _apply_portfolio_turnover_budget(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    return _apply_portfolio_turnover_budget_impl(rows, spec)


def _apply_portfolio_signal_limit(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    return _apply_portfolio_signal_limit_impl(rows, spec)


def _apply_portfolio_exposure_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    return _apply_portfolio_exposure_limits_impl(rows, spec)


def _apply_portfolio_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return _apply_portfolio_net_exposure_limit_impl(
        rows,
        max_abs_net_position_weight=max_abs_net_position_weight,
        spec=spec,
    )


def _apply_portfolio_group_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_group_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return _apply_portfolio_group_net_exposure_limit_impl(
        rows,
        max_group_abs_net_position_weight=max_group_abs_net_position_weight,
        spec=spec,
    )
