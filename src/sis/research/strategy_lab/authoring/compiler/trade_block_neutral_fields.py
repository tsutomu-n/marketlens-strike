from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.contracts.base import DEFAULT_EXIT_PRIORITY


def _blocked_trade_neutral_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stop_loss_bps": None,
        "take_profit_bps": None,
        "min_reward_risk_ratio": row.get("min_reward_risk_ratio"),
        "reward_risk_ratio": row.get("reward_risk_ratio"),
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
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "entry_reduce_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "min_fill_fraction": None,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "_cross_sectional_group": row.get("_cross_sectional_group"),
        "_portfolio_group": row.get("_portfolio_group"),
        "_portfolio_turnover_weight": row.get("_portfolio_turnover_weight"),
    }
