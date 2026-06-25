from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import ExitRules
from sis.research.strategy_lab.authoring.exit_required_columns import (
    _exit_required_columns,
)


def test_exit_required_columns_collects_explicit_exit_columns() -> None:
    rules = ExitRules(
        stop_loss_bps_column="stop",
        min_stop_loss_bps_column="min_stop",
        max_stop_loss_bps_column="max_stop",
        take_profit_bps_column="take",
        min_take_profit_bps_column="min_take",
        max_take_profit_bps_column="max_take",
        min_reward_risk_ratio_column="min_rr",
        trailing_stop_bps_column="trailing",
        trailing_stop_activation_bps_column="trailing_activation",
        partial_take_profit_bps_column="partial_take",
        partial_exit_fraction_column="partial_fraction",
        min_holding_minutes_column="min_hold",
        max_holding_minutes_column="max_hold",
        reduce_fraction_column="reduce_fraction",
        add_fraction_column="add_fraction",
        rebalance_target_fraction_column="rebalance_target",
        rebalance_min_delta_fraction_column="rebalance_min_delta",
    )

    assert _exit_required_columns(rules) == {
        "stop",
        "min_stop",
        "max_stop",
        "take",
        "min_take",
        "max_take",
        "min_rr",
        "trailing",
        "trailing_activation",
        "partial_take",
        "partial_fraction",
        "min_hold",
        "max_hold",
        "reduce_fraction",
        "add_fraction",
        "rebalance_target",
        "rebalance_min_delta",
    }


def test_exit_required_columns_returns_empty_set_when_disabled() -> None:
    assert _exit_required_columns(ExitRules()) == set()
