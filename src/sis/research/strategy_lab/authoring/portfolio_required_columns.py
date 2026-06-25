from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules


def _portfolio_required_columns(portfolio: PortfolioRules) -> set[str]:
    columns: set[str] = set()
    for column_name in (
        portfolio.allocation_volatility_column,
        portfolio.allocation_beta_column,
        portfolio.target_total_position_weight_column,
        portfolio.max_total_position_weight_column,
        portfolio.max_long_position_weight_column,
        portfolio.max_short_position_weight_column,
        portfolio.max_abs_net_position_weight_column,
        portfolio.max_symbol_position_weight_column,
        portfolio.max_group_position_weight_column,
        portfolio.max_group_abs_net_position_weight_column,
        portfolio.group_column,
        portfolio.turnover_weight_column,
    ):
        if column_name is not None:
            columns.add(column_name)
    return columns
