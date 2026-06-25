from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_gross import (
    _PortfolioExposureState,
    _accepted_portfolio_exposure_state,
    _portfolio_exposure_block_reason,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_net import (
    _apply_portfolio_group_net_exposure_limit,
    _apply_portfolio_net_exposure_limit,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_ranked_rows import (
    _portfolio_exposure_ranked_rows,
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
from sis.research.strategy_lab.authoring.compiler.trade_blocking import _block_trade_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_exposure_timestamp_group_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    max_total_position_weight = _portfolio_max_total_position_weight(rows, portfolio)
    max_long_position_weight = _portfolio_max_long_position_weight(rows, portfolio)
    max_short_position_weight = _portfolio_max_short_position_weight(rows, portfolio)
    max_symbol_position_weight = _portfolio_max_symbol_position_weight(rows, portfolio)
    max_group_position_weight = _portfolio_max_group_position_weight(rows, portfolio)
    max_abs_net_position_weight = _portfolio_max_abs_net_position_weight(rows, portfolio)
    max_group_abs_net_position_weight = _portfolio_max_group_abs_net_position_weight(
        rows, portfolio
    )
    exposure_state = _PortfolioExposureState()
    accepted_rows: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    for row in _portfolio_exposure_ranked_rows(rows):
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
    return [*blocked_rows, *net_blocked_rows, *group_net_blocked_rows, *accepted_rows]
