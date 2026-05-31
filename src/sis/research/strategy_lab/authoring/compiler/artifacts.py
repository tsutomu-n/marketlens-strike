from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from sis.backtest.signals import ResearchSignal
from sis.research.signal_builder import _legacy_export
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    strategy_signal_manifest_path,
    write_strategy_signal_manifest,
)


def write_authoring_signal_artifacts(
    frame: pl.DataFrame, manifest: StrategySignalManifest, *, data_dir: Path
) -> dict[str, Path]:
    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    legacy_out = data_dir / "research/signals.csv"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(parquet_out)
    with jsonl_out.open("w", encoding="utf-8") as handle:
        for row in frame.to_dicts():
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    _legacy_export(frame).write_csv(legacy_out)
    write_strategy_signal_manifest(manifest, strategy_signal_manifest_path(data_dir))
    return {
        "signals_parquet": parquet_out,
        "signals_jsonl": jsonl_out,
        "legacy_csv": legacy_out,
        "manifest": strategy_signal_manifest_path(data_dir),
    }


def strategy_signals_to_research_signals(frame: pl.DataFrame) -> list[ResearchSignal]:
    if frame.is_empty():
        return []
    return [
        ResearchSignal(
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
            slippage_bps=row.get("slippage_bps") or 0.0,
            max_fill_fraction=row.get("max_fill_fraction") or 1.0,
            min_fill_fraction=row.get("min_fill_fraction"),
            max_spread_bps=row.get("max_spread_bps"),
            min_depth_usd=row.get("min_depth_usd"),
            depth_column=row.get("depth_column"),
            depth_participation_rate=row.get("depth_participation_rate") or 1.0,
            max_latency_ms=row.get("max_latency_ms"),
            latency_ms=row.get("latency_ms"),
            min_queue_position_score=row.get("min_queue_position_score"),
            queue_position_score=row.get("queue_position_score"),
            min_borrow_availability_ratio=row.get("min_borrow_availability_ratio"),
            borrow_availability_ratio=row.get("borrow_availability_ratio"),
            max_borrow_cost_bps=row.get("max_borrow_cost_bps"),
            borrow_cost_bps=row.get("borrow_cost_bps"),
            max_tax_drag_bps=row.get("max_tax_drag_bps"),
            tax_drag_bps=row.get("tax_drag_bps"),
            max_turnover_pressure=row.get("max_turnover_pressure"),
            turnover_pressure=row.get("turnover_pressure"),
            max_capacity_usage_ratio=row.get("max_capacity_usage_ratio"),
            capacity_usage_ratio=row.get("capacity_usage_ratio"),
            max_correlation_crowding_score=row.get("max_correlation_crowding_score"),
            correlation_crowding_score=row.get("correlation_crowding_score"),
            min_fee_edge_bps=row.get("min_fee_edge_bps"),
            fee_edge_bps=row.get("fee_edge_bps"),
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
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower()
        in {"long", "short", "close", "reduce", "add", "rebalance"}
    ]
