from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import _block_trade_row
from sis.research.strategy_lab.authoring.compiler.portfolio_allocation import (
    _apply_portfolio_allocation as _apply_portfolio_allocation_impl,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_gross import (
    _PortfolioExposureState,
    _accepted_portfolio_exposure_state,
    _portfolio_exposure_block_reason,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_net import (
    _apply_portfolio_group_net_exposure_limit as _apply_portfolio_group_net_exposure_limit_impl,
    _apply_portfolio_net_exposure_limit as _apply_portfolio_net_exposure_limit_impl,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_limit_resolution import (
    _portfolio_max_abs_net_position_weight,
    _portfolio_max_group_abs_net_position_weight,
    _portfolio_max_group_position_weight,
    _portfolio_max_long_position_weight,
    _portfolio_max_short_position_weight,
    _portfolio_max_symbol_position_weight,
    _portfolio_max_total_position_weight,
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
    portfolio = spec.rules.portfolio
    if not portfolio.exposure_limits_enabled:
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
        max_total_position_weight = _portfolio_max_total_position_weight(timestamp_rows, portfolio)
        max_long_position_weight = _portfolio_max_long_position_weight(timestamp_rows, portfolio)
        max_short_position_weight = _portfolio_max_short_position_weight(timestamp_rows, portfolio)
        max_symbol_position_weight = _portfolio_max_symbol_position_weight(
            timestamp_rows, portfolio
        )
        max_group_position_weight = _portfolio_max_group_position_weight(timestamp_rows, portfolio)
        max_abs_net_position_weight = _portfolio_max_abs_net_position_weight(
            timestamp_rows, portfolio
        )
        max_group_abs_net_position_weight = _portfolio_max_group_abs_net_position_weight(
            timestamp_rows, portfolio
        )
        exposure_state = _PortfolioExposureState()
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            reason = _portfolio_exposure_block_reason(
                row,
                portfolio=portfolio,
                max_total_position_weight=max_total_position_weight,
                max_long_position_weight=max_long_position_weight,
                max_short_position_weight=max_short_position_weight,
                max_symbol_position_weight=max_symbol_position_weight,
                max_group_position_weight=max_group_position_weight,
                state=exposure_state,
            )
            if reason is not None:
                blocked_rows.append(_block_trade_row(row, spec=spec, block_reason=reason))
                continue
            exposure_state = _accepted_portfolio_exposure_state(exposure_state, row)
            accepted_rows.append(row)
        accepted_rows, net_blocked_rows = _apply_portfolio_net_exposure_limit(
            accepted_rows,
            max_abs_net_position_weight=max_abs_net_position_weight,
            spec=spec,
        )
        accepted_rows, group_net_blocked_rows = _apply_portfolio_group_net_exposure_limit(
            accepted_rows,
            max_group_abs_net_position_weight=max_group_abs_net_position_weight,
            spec=spec,
        )
        selected.extend([*blocked_rows, *net_blocked_rows, *group_net_blocked_rows, *accepted_rows])
    return selected


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
