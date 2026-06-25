from __future__ import annotations

from typing import Any, Literal, cast

from sis.research.strategy_lab.authoring.contracts.base import DEFAULT_EXIT_PRIORITY


def _paper_preview_exit_fields(*, row: dict[str, Any], selected: bool) -> dict[str, Any]:
    use_row = selected and bool(row)
    return {
        "stop_loss_bps": row.get("stop_loss_bps") if use_row else None,
        "min_stop_loss_bps": row.get("min_stop_loss_bps") if use_row else None,
        "max_stop_loss_bps": row.get("max_stop_loss_bps") if use_row else None,
        "take_profit_bps": row.get("take_profit_bps") if use_row else None,
        "min_take_profit_bps": row.get("min_take_profit_bps") if use_row else None,
        "max_take_profit_bps": row.get("max_take_profit_bps") if use_row else None,
        "min_reward_risk_ratio": row.get("min_reward_risk_ratio") if use_row else None,
        "reward_risk_ratio": row.get("reward_risk_ratio") if use_row else None,
        "trailing_stop_bps": row.get("trailing_stop_bps") if use_row else None,
        "trailing_stop_activation_bps": row.get("trailing_stop_activation_bps")
        if use_row
        else None,
        "partial_take_profit_bps": row.get("partial_take_profit_bps") if use_row else None,
        "partial_exit_fraction": row.get("partial_exit_fraction") if use_row else None,
        "min_holding_minutes": row.get("min_holding_minutes") if use_row else None,
        "max_holding_minutes": row.get("max_holding_minutes") if use_row else None,
        "exit_priority": str(row.get("exit_priority") or DEFAULT_EXIT_PRIORITY)
        if use_row
        else DEFAULT_EXIT_PRIORITY,
        "exit_on_opposite_signal": bool(row.get("exit_on_opposite_signal")) if use_row else False,
        "bracket_type": cast(
            Literal["none", "oco"],
            row.get("bracket_type") if use_row else "none",
        ),
        "bracket_time_stop_minutes": row.get("bracket_time_stop_minutes") if use_row else None,
        "bracket_break_even_after_bps": row.get("bracket_break_even_after_bps")
        if use_row
        else None,
        "bracket_break_even_after_partial_take_profit": bool(
            row.get("bracket_break_even_after_partial_take_profit")
        )
        if use_row
        else False,
    }
