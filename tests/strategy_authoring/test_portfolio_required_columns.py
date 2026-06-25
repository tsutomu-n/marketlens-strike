from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules
from sis.research.strategy_lab.authoring.portfolio_required_columns import (
    _portfolio_required_columns,
)


def test_portfolio_required_columns_collect_all_configured_portfolio_columns() -> None:
    columns = _portfolio_required_columns(
        PortfolioRules(
            allocation_method="group_neutral",
            target_total_position_weight_column="target_weight",
            allocation_volatility_column="allocation_vol",
            allocation_beta_column="allocation_beta",
            max_total_position_weight_column="max_total",
            max_long_position_weight_column="max_long",
            max_short_position_weight_column="max_short",
            max_abs_net_position_weight_column="max_net",
            max_symbol_position_weight_column="max_symbol",
            max_group_position_weight_column="max_group",
            max_group_abs_net_position_weight_column="max_group_net",
            group_column="sector_bucket",
            turnover_weight_column="turnover_weight",
        )
    )

    assert columns == {
        "target_weight",
        "allocation_vol",
        "allocation_beta",
        "max_total",
        "max_long",
        "max_short",
        "max_net",
        "max_symbol",
        "max_group",
        "max_group_net",
        "sector_bucket",
        "turnover_weight",
    }


def test_portfolio_required_columns_skip_unconfigured_columns() -> None:
    assert _portfolio_required_columns(PortfolioRules()) == set()
