from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_numeric_values import _optional_float_from_row


def _trade_portfolio_fields(*, row: dict[str, Any], spec: Any) -> dict[str, Any]:
    portfolio = spec.rules.portfolio
    cross_sectional = spec.rules.cross_sectional
    return {
        "_cross_sectional_group": row.get(cross_sectional.group_column)
        if cross_sectional.group_column is not None
        else None,
        "_allocation_volatility": row.get(portfolio.allocation_volatility_column)
        if portfolio.allocation_volatility_column is not None
        else None,
        "_allocation_beta": row.get(portfolio.allocation_beta_column)
        if portfolio.allocation_beta_column is not None
        else None,
        "_portfolio_target_total_position_weight": _optional_float_from_row(
            row, portfolio.target_total_position_weight_column
        )
        if portfolio.target_total_position_weight_column is not None
        else None,
        "_portfolio_max_total_position_weight": _optional_float_from_row(
            row, portfolio.max_total_position_weight_column
        )
        if portfolio.max_total_position_weight_column is not None
        else None,
        "_portfolio_max_long_position_weight": _optional_float_from_row(
            row, portfolio.max_long_position_weight_column
        )
        if portfolio.max_long_position_weight_column is not None
        else None,
        "_portfolio_max_short_position_weight": _optional_float_from_row(
            row, portfolio.max_short_position_weight_column
        )
        if portfolio.max_short_position_weight_column is not None
        else None,
        "_portfolio_max_abs_net_position_weight": _optional_float_from_row(
            row, portfolio.max_abs_net_position_weight_column
        )
        if portfolio.max_abs_net_position_weight_column is not None
        else None,
        "_portfolio_max_symbol_position_weight": _optional_float_from_row(
            row, portfolio.max_symbol_position_weight_column
        )
        if portfolio.max_symbol_position_weight_column is not None
        else None,
        "_portfolio_max_group_position_weight": _optional_float_from_row(
            row, portfolio.max_group_position_weight_column
        )
        if portfolio.max_group_position_weight_column is not None
        else None,
        "_portfolio_max_group_abs_net_position_weight": _optional_float_from_row(
            row, portfolio.max_group_abs_net_position_weight_column
        )
        if portfolio.max_group_abs_net_position_weight_column is not None
        else None,
        "_portfolio_group": row.get(portfolio.group_column)
        if portfolio.group_column is not None
        else None,
        "_portfolio_turnover_weight": row.get(portfolio.turnover_weight_column)
        if portfolio.turnover_weight_column is not None
        else None,
    }
