from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_exit_fields import (
    _trade_exit_fields,
)


def _exit(**overrides):
    defaults = {
        "stop_loss_bps": None,
        "stop_loss_bps_column": None,
        "min_stop_loss_bps": None,
        "min_stop_loss_bps_column": None,
        "max_stop_loss_bps": None,
        "max_stop_loss_bps_column": None,
        "take_profit_bps": None,
        "take_profit_bps_column": None,
        "min_take_profit_bps": None,
        "min_take_profit_bps_column": None,
        "max_take_profit_bps": None,
        "max_take_profit_bps_column": None,
        "min_reward_risk_ratio": None,
        "min_reward_risk_ratio_column": None,
        "trailing_stop_bps": None,
        "trailing_stop_bps_column": None,
        "trailing_stop_activation_bps": None,
        "trailing_stop_activation_bps_column": None,
        "partial_take_profit_bps": None,
        "partial_take_profit_bps_column": None,
        "partial_exit_fraction": None,
        "partial_exit_fraction_column": None,
        "min_holding_minutes": None,
        "min_holding_minutes_column": None,
        "max_holding_minutes": None,
        "max_holding_minutes_column": None,
        "exit_priority": [
            "take_profit",
            "partial_take_profit",
            "stop_loss",
            "trailing_stop",
            "break_even_stop",
            "time_stop",
        ],
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "reduce_fraction_column": None,
        "exit_on_add_signal": False,
        "exit_on_rebalance_signal": False,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
        "min_reward_risk_ratio": None,
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_exit_fields_resolve_defaults() -> None:
    fields = _trade_exit_fields(row={}, exit_rules=_exit(), reduce_only=False)

    assert fields == {
        "stop_loss_bps": None,
        "min_stop_loss_bps": None,
        "max_stop_loss_bps": None,
        "take_profit_bps": None,
        "min_take_profit_bps": None,
        "max_take_profit_bps": None,
        "min_reward_risk_ratio": None,
        "reward_risk_ratio": None,
        "trailing_stop_bps": None,
        "trailing_stop_activation_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "max_holding_minutes": None,
        "exit_priority": "take_profit,partial_take_profit,stop_loss,trailing_stop,break_even_stop,time_stop",
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "exit_on_add_signal": False,
        "add_fraction": None,
        "exit_on_rebalance_signal": False,
        "rebalance_target_fraction": None,
        "rebalance_min_delta_fraction": None,
    }


def test_trade_exit_fields_use_row_columns_and_leg_overrides() -> None:
    fields = _trade_exit_fields(
        row={
            "row_stop": 999.0,
            "row_min_stop": 80.0,
            "row_max_stop": 200.0,
            "row_take": 888.0,
            "row_min_take": 250.0,
            "row_max_take": 400.0,
            "row_min_rr": 1.5,
            "row_trailing": 50.0,
            "row_trailing_activation": 10.0,
            "row_partial_take": 100.0,
            "row_partial_fraction": 0.25,
            "row_min_hold": "30",
            "row_max_hold": 60,
            "row_reduce_fraction": 0.6,
        },
        exit_rules=_exit(
            stop_loss_bps_column="row_stop",
            min_stop_loss_bps_column="row_min_stop",
            max_stop_loss_bps_column="row_max_stop",
            take_profit_bps_column="row_take",
            min_take_profit_bps_column="row_min_take",
            max_take_profit_bps_column="row_max_take",
            min_reward_risk_ratio_column="row_min_rr",
            trailing_stop_bps_column="row_trailing",
            trailing_stop_activation_bps_column="row_trailing_activation",
            partial_take_profit_bps_column="row_partial_take",
            partial_exit_fraction_column="row_partial_fraction",
            min_holding_minutes_column="row_min_hold",
            max_holding_minutes_column="row_max_hold",
            reduce_fraction_column="row_reduce_fraction",
            exit_on_reduce_signal=True,
        ),
        reduce_only=True,
        exit_overrides={
            "stop_loss_bps": 120.0,
            "take_profit_bps": 220.0,
        },
    )

    assert fields["stop_loss_bps"] == 120.0
    assert fields["min_stop_loss_bps"] == 80.0
    assert fields["max_stop_loss_bps"] == 200.0
    assert fields["take_profit_bps"] == 220.0
    assert fields["min_take_profit_bps"] == 250.0
    assert fields["max_take_profit_bps"] == 400.0
    assert fields["min_reward_risk_ratio"] == 1.5
    assert fields["trailing_stop_bps"] == 50.0
    assert fields["trailing_stop_activation_bps"] == 10.0
    assert fields["partial_take_profit_bps"] == 100.0
    assert fields["partial_exit_fraction"] == 0.25
    assert fields["min_holding_minutes"] == 30
    assert fields["max_holding_minutes"] == 60
    assert fields["exit_on_reduce_signal"] is True
    assert fields["reduce_fraction"] == 0.6


def test_trade_exit_fields_gate_reduce_fraction_by_reduce_only() -> None:
    fields = _trade_exit_fields(
        row={"row_reduce_fraction": 0.6},
        exit_rules=_exit(reduce_fraction=0.5, reduce_fraction_column="row_reduce_fraction"),
        reduce_only=False,
    )

    assert fields["reduce_fraction"] is None


def test_trade_exit_fields_use_regime_fallbacks() -> None:
    fields = _trade_exit_fields(
        row={},
        exit_rules=_exit(),
        reduce_only=True,
        regime=_regime(
            stop_loss_bps=90.0,
            take_profit_bps=180.0,
            min_reward_risk_ratio=2.0,
            trailing_stop_bps=70.0,
            partial_exit_fraction=0.4,
        ),
    )

    assert fields["stop_loss_bps"] == 90.0
    assert fields["take_profit_bps"] == 180.0
    assert fields["min_reward_risk_ratio"] == 2.0
    assert fields["trailing_stop_bps"] == 70.0
    assert fields["partial_exit_fraction"] == 0.4
