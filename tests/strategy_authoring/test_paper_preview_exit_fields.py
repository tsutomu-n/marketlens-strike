from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.paper_preview_exit_fields import (
    _paper_preview_exit_fields,
)
from sis.research.strategy_lab.authoring.contracts.base import DEFAULT_EXIT_PRIORITY


def test_paper_preview_exit_fields_use_selected_row_values() -> None:
    fields = _paper_preview_exit_fields(
        row={
            "stop_loss_bps": 100.0,
            "min_stop_loss_bps": 80.0,
            "max_stop_loss_bps": 140.0,
            "take_profit_bps": 220.0,
            "min_take_profit_bps": 180.0,
            "max_take_profit_bps": 260.0,
            "min_reward_risk_ratio": 1.5,
            "reward_risk_ratio": 2.2,
            "trailing_stop_bps": 60.0,
            "trailing_stop_activation_bps": 30.0,
            "partial_take_profit_bps": 120.0,
            "partial_exit_fraction": 0.4,
            "min_holding_minutes": 15,
            "max_holding_minutes": 120,
            "exit_priority": "stop_loss,take_profit,time_stop",
            "exit_on_opposite_signal": 1,
            "bracket_type": "oco",
            "bracket_time_stop_minutes": 45,
            "bracket_break_even_after_bps": 25.0,
            "bracket_break_even_after_partial_take_profit": True,
        },
        selected=True,
    )

    assert fields == {
        "stop_loss_bps": 100.0,
        "min_stop_loss_bps": 80.0,
        "max_stop_loss_bps": 140.0,
        "take_profit_bps": 220.0,
        "min_take_profit_bps": 180.0,
        "max_take_profit_bps": 260.0,
        "min_reward_risk_ratio": 1.5,
        "reward_risk_ratio": 2.2,
        "trailing_stop_bps": 60.0,
        "trailing_stop_activation_bps": 30.0,
        "partial_take_profit_bps": 120.0,
        "partial_exit_fraction": 0.4,
        "min_holding_minutes": 15,
        "max_holding_minutes": 120,
        "exit_priority": "stop_loss,take_profit,time_stop",
        "exit_on_opposite_signal": True,
        "bracket_type": "oco",
        "bracket_time_stop_minutes": 45,
        "bracket_break_even_after_bps": 25.0,
        "bracket_break_even_after_partial_take_profit": True,
    }


def test_paper_preview_exit_fields_preserve_unselected_defaults() -> None:
    fields = _paper_preview_exit_fields(
        row={
            "stop_loss_bps": 100.0,
            "exit_priority": "stop_loss",
            "exit_on_opposite_signal": True,
            "bracket_type": "oco",
            "bracket_break_even_after_partial_take_profit": True,
        },
        selected=False,
    )

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
        "exit_priority": DEFAULT_EXIT_PRIORITY,
        "exit_on_opposite_signal": False,
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "bracket_break_even_after_partial_take_profit": False,
    }
