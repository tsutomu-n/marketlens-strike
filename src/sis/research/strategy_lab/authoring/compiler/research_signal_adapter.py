from __future__ import annotations

import polars as pl

from sis.backtest.signals import ResearchSignal
from sis.research.strategy_lab.authoring.compiler.research_signal_execution_fields import (
    _research_signal_execution_fields,
)


def _research_signal_from_strategy_row(row: dict) -> ResearchSignal:
    return ResearchSignal(
        ts_signal=row["ts_signal"],
        canonical_symbol=str(row["execution_symbol"]).upper(),
        side=str(row["side"]).lower(),
        timeframe=str(row["timeframe"]).lower(),
        signal_strength=row.get("raw_score"),
        stop_loss_bps=row.get("stop_loss_bps"),
        min_stop_loss_bps=row.get("min_stop_loss_bps"),
        max_stop_loss_bps=row.get("max_stop_loss_bps"),
        take_profit_bps=row.get("take_profit_bps"),
        min_take_profit_bps=row.get("min_take_profit_bps"),
        max_take_profit_bps=row.get("max_take_profit_bps"),
        min_reward_risk_ratio=row.get("min_reward_risk_ratio"),
        reward_risk_ratio=row.get("reward_risk_ratio"),
        trailing_stop_bps=row.get("trailing_stop_bps"),
        trailing_stop_activation_bps=row.get("trailing_stop_activation_bps"),
        partial_take_profit_bps=row.get("partial_take_profit_bps"),
        partial_exit_fraction=row.get("partial_exit_fraction"),
        min_holding_minutes=row.get("min_holding_minutes"),
        max_holding_minutes=row.get("max_holding_minutes"),
        exit_priority=str(row.get("exit_priority") or ""),
        exit_on_opposite_signal=bool(row.get("exit_on_opposite_signal")),
        exit_on_close_signal=bool(row.get("exit_on_close_signal")),
        exit_on_reduce_signal=bool(row.get("exit_on_reduce_signal")),
        reduce_fraction=row.get("reduce_fraction"),
        exit_on_add_signal=bool(row.get("exit_on_add_signal")),
        add_fraction=row.get("add_fraction"),
        exit_on_rebalance_signal=bool(row.get("exit_on_rebalance_signal")),
        rebalance_target_fraction=row.get("rebalance_target_fraction"),
        rebalance_min_delta_fraction=row.get("rebalance_min_delta_fraction"),
        bracket_type=str(row.get("bracket_type") or "none"),
        bracket_time_stop_minutes=row.get("bracket_time_stop_minutes"),
        bracket_break_even_after_bps=row.get("bracket_break_even_after_bps"),
        bracket_break_even_after_partial_take_profit=bool(
            row.get("bracket_break_even_after_partial_take_profit")
        ),
        entry_order_type=str(row.get("entry_order_type") or "market"),
        entry_limit_offset_bps=row.get("entry_limit_offset_bps"),
        entry_stop_offset_bps=row.get("entry_stop_offset_bps"),
        entry_timeout_minutes=row.get("entry_timeout_minutes"),
        entry_time_in_force=str(row.get("entry_time_in_force") or "gtc"),
        entry_post_only=bool(row.get("entry_post_only")),
        entry_reduce_only=bool(row.get("entry_reduce_only")),
        **_research_signal_execution_fields(row),
        position_weight=row.get("position_weight") or 1.0,
        notional_usd=row.get("notional_usd"),
        signal_id=str(row.get("signal_id") or "") or None,
        multi_leg_group_id=str(row.get("multi_leg_group_id") or "") or None,
        multi_leg_leg_index=row.get("multi_leg_leg_index"),
        multi_leg_leg_count=row.get("multi_leg_leg_count"),
        multi_leg_anchor_real_market_symbol=(
            str(row.get("multi_leg_anchor_real_market_symbol") or "") or None
        ),
    )


def strategy_signals_to_research_signals(frame: pl.DataFrame) -> list[ResearchSignal]:
    if frame.is_empty():
        return []
    return [
        _research_signal_from_strategy_row(row)
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower()
        in {"long", "short", "close", "reduce", "add", "rebalance"}
    ]
