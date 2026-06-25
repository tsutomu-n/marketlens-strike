from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_portfolio_fields import (
    _trade_portfolio_fields,
)


def _spec(*, cross_sectional: object, portfolio: object):
    return SimpleNamespace(
        rules=SimpleNamespace(
            cross_sectional=cross_sectional,
            portfolio=portfolio,
        )
    )


def _cross_sectional(**overrides):
    defaults = {"group_column": None}
    return SimpleNamespace(**{**defaults, **overrides})


def _portfolio(**overrides):
    defaults = {
        "allocation_volatility_column": None,
        "allocation_beta_column": None,
        "target_total_position_weight_column": None,
        "max_total_position_weight_column": None,
        "max_long_position_weight_column": None,
        "max_short_position_weight_column": None,
        "max_abs_net_position_weight_column": None,
        "max_symbol_position_weight_column": None,
        "max_group_position_weight_column": None,
        "max_group_abs_net_position_weight_column": None,
        "group_column": None,
        "turnover_weight_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_portfolio_fields_resolve_configured_columns() -> None:
    fields = _trade_portfolio_fields(
        row={
            "cross_group": "growth",
            "allocation_vol": "0.15",
            "allocation_beta": 1.25,
            "target_weight": "0.90",
            "max_total": 1.1,
            "max_long": "0.70",
            "max_short": " ",
            "max_symbol": "0.45",
            "max_group": 0.8,
            "max_group_abs_net": "0.35",
            "portfolio_group": "tech",
            "turnover_weight": "0.42",
        },
        spec=_spec(
            cross_sectional=_cross_sectional(group_column="cross_group"),
            portfolio=_portfolio(
                allocation_volatility_column="allocation_vol",
                allocation_beta_column="allocation_beta",
                target_total_position_weight_column="target_weight",
                max_total_position_weight_column="max_total",
                max_long_position_weight_column="max_long",
                max_short_position_weight_column="max_short",
                max_abs_net_position_weight_column="missing_abs_net",
                max_symbol_position_weight_column="max_symbol",
                max_group_position_weight_column="max_group",
                max_group_abs_net_position_weight_column="max_group_abs_net",
                group_column="portfolio_group",
                turnover_weight_column="turnover_weight",
            ),
        ),
    )

    assert fields == {
        "_cross_sectional_group": "growth",
        "_allocation_volatility": "0.15",
        "_allocation_beta": 1.25,
        "_portfolio_target_total_position_weight": 0.9,
        "_portfolio_max_total_position_weight": 1.1,
        "_portfolio_max_long_position_weight": 0.7,
        "_portfolio_max_short_position_weight": None,
        "_portfolio_max_abs_net_position_weight": None,
        "_portfolio_max_symbol_position_weight": 0.45,
        "_portfolio_max_group_position_weight": 0.8,
        "_portfolio_max_group_abs_net_position_weight": 0.35,
        "_portfolio_group": "tech",
        "_portfolio_turnover_weight": "0.42",
    }


def test_trade_portfolio_fields_keep_none_keys_when_columns_are_absent() -> None:
    fields = _trade_portfolio_fields(
        row={},
        spec=_spec(
            cross_sectional=_cross_sectional(),
            portfolio=_portfolio(),
        ),
    )

    assert fields == {
        "_cross_sectional_group": None,
        "_allocation_volatility": None,
        "_allocation_beta": None,
        "_portfolio_target_total_position_weight": None,
        "_portfolio_max_total_position_weight": None,
        "_portfolio_max_long_position_weight": None,
        "_portfolio_max_short_position_weight": None,
        "_portfolio_max_abs_net_position_weight": None,
        "_portfolio_max_symbol_position_weight": None,
        "_portfolio_max_group_position_weight": None,
        "_portfolio_max_group_abs_net_position_weight": None,
        "_portfolio_group": None,
        "_portfolio_turnover_weight": None,
    }
