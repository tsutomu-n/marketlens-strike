from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_gross import (
    _PortfolioExposureState,
    _accepted_portfolio_exposure_state,
    _portfolio_exposure_block_reason,
)


def _portfolio(**overrides):
    defaults = {
        "max_group_abs_net_position_weight": None,
        "max_group_abs_net_position_weight_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_portfolio_exposure_state_updates_total_side_symbol_and_group_weights() -> None:
    state = _accepted_portfolio_exposure_state(
        _PortfolioExposureState(),
        {
            "side": "long",
            "position_weight": -0.4,
            "execution_symbol": "AAA100",
            "_portfolio_group": "tech",
        },
    )
    state = _accepted_portfolio_exposure_state(
        state,
        {
            "side": "short",
            "position_weight": 0.3,
            "execution_symbol": "BBB100",
            "_portfolio_group": "tech",
        },
    )

    assert state.total_weight == 0.7
    assert state.long_weight == 0.4
    assert state.short_weight == 0.3
    assert state.symbol_weights == {"AAA100": 0.4, "BBB100": 0.3}
    assert state.group_weights == {"tech": 0.7}


def test_portfolio_exposure_block_reason_preserves_precedence() -> None:
    row = {
        "side": "long",
        "position_weight": 0.5,
        "execution_symbol": "AAA100",
        "_portfolio_group": "tech",
    }
    state = _PortfolioExposureState(
        total_weight=0.7,
        long_weight=0.2,
        short_weight=0.0,
        symbol_weights={"AAA100": 0.1},
        group_weights={"tech": 0.1},
    )

    assert (
        _portfolio_exposure_block_reason(
            row,
            portfolio=_portfolio(),
            max_total_position_weight=1.0,
            max_long_position_weight=0.4,
            max_short_position_weight=None,
            max_symbol_position_weight=0.4,
            max_group_position_weight=0.4,
            state=state,
        )
        == "portfolio_total_exposure_limit"
    )


def test_portfolio_exposure_block_reason_checks_side_symbol_and_group_limits() -> None:
    state = _PortfolioExposureState(
        total_weight=0.2,
        long_weight=0.2,
        short_weight=0.3,
        symbol_weights={"AAA100": 0.3},
        group_weights={"tech": 0.3},
    )

    assert (
        _portfolio_exposure_block_reason(
            {
                "side": "short",
                "position_weight": 0.3,
                "execution_symbol": "BBB100",
                "_portfolio_group": "macro",
            },
            portfolio=_portfolio(),
            max_total_position_weight=2.0,
            max_long_position_weight=None,
            max_short_position_weight=0.5,
            max_symbol_position_weight=None,
            max_group_position_weight=None,
            state=state,
        )
        == "portfolio_short_exposure_limit"
    )
    assert (
        _portfolio_exposure_block_reason(
            {
                "side": "long",
                "position_weight": 0.3,
                "execution_symbol": "AAA100",
                "_portfolio_group": "macro",
            },
            portfolio=_portfolio(),
            max_total_position_weight=2.0,
            max_long_position_weight=None,
            max_short_position_weight=None,
            max_symbol_position_weight=0.5,
            max_group_position_weight=None,
            state=state,
        )
        == "portfolio_symbol_exposure_limit"
    )
    assert (
        _portfolio_exposure_block_reason(
            {
                "side": "long",
                "position_weight": 0.3,
                "execution_symbol": "CCC100",
                "_portfolio_group": "tech",
            },
            portfolio=_portfolio(),
            max_total_position_weight=2.0,
            max_long_position_weight=None,
            max_short_position_weight=None,
            max_symbol_position_weight=None,
            max_group_position_weight=0.5,
            state=state,
        )
        == "portfolio_group_exposure_limit"
    )


def test_portfolio_exposure_block_reason_requires_group_for_gross_or_net_group_limits() -> None:
    row = {"side": "long", "position_weight": 0.3, "execution_symbol": "AAA100"}

    assert (
        _portfolio_exposure_block_reason(
            row,
            portfolio=_portfolio(),
            max_total_position_weight=None,
            max_long_position_weight=None,
            max_short_position_weight=None,
            max_symbol_position_weight=None,
            max_group_position_weight=1.0,
            state=_PortfolioExposureState(),
        )
        == "portfolio_group_missing"
    )
    assert (
        _portfolio_exposure_block_reason(
            row,
            portfolio=_portfolio(max_group_abs_net_position_weight=1.0),
            max_total_position_weight=None,
            max_long_position_weight=None,
            max_short_position_weight=None,
            max_symbol_position_weight=None,
            max_group_position_weight=None,
            state=_PortfolioExposureState(),
        )
        == "portfolio_group_missing"
    )
