from __future__ import annotations

from typing import Iterable

import polars as pl

from sis.research.strategy_lab.specs import StrategySignalRecord, SymbolBinding

REQUIRED_SIGNAL_COLUMNS = {
    "schema_version",
    "signal_id",
    "generated_at",
    "strategy_id",
    "strategy_family",
    "strategy_version",
    "ts_signal",
    "timeframe",
    "execution_venue",
    "execution_symbol",
    "real_market_symbol",
    "side",
    "confidence",
    "tail_bucket",
}


def _binding_keys(symbol_bindings: Iterable[SymbolBinding]) -> set[tuple[str, str, str]]:
    return {
        (
            binding.execution_venue,
            binding.execution_symbol.upper(),
            binding.real_market_symbol.upper(),
        )
        for binding in symbol_bindings
    }


def validate_strategy_signal_frame(
    frame: pl.DataFrame,
    *,
    symbol_bindings: Iterable[SymbolBinding],
) -> pl.DataFrame:
    missing = REQUIRED_SIGNAL_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Strategy signal frame missing columns: {sorted(missing)}")
    if frame.is_empty():
        return frame

    allowed_bindings = _binding_keys(symbol_bindings)
    records: list[dict] = []
    for row in frame.to_dicts():
        signal = StrategySignalRecord(
            schema_version=row["schema_version"],
            signal_id=str(row["signal_id"]),
            generated_at=row["generated_at"],
            strategy_id=str(row["strategy_id"]),
            strategy_family=str(row["strategy_family"]),
            strategy_version=str(row["strategy_version"]),
            trial_id=row.get("trial_id"),
            parameter_hash=row.get("parameter_hash"),
            ts_signal=row["ts_signal"],
            timeframe=str(row["timeframe"]),
            execution_venue=row["execution_venue"],
            execution_symbol=str(row["execution_symbol"]),
            real_market_symbol=str(row["real_market_symbol"]),
            side=row["side"],
            raw_score=row.get("raw_score"),
            rank_score=row.get("rank_score"),
            percentile_rank=row.get("percentile_rank"),
            tail_bucket=row["tail_bucket"],
            confidence=float(row["confidence"]),
            source_confidence=row.get("source_confidence"),
            venue_quality_score=row.get("venue_quality_score"),
            feature_snapshot_ref=row.get("feature_snapshot_ref"),
            quote_ref=row.get("quote_ref"),
            tracking_ref=row.get("tracking_ref"),
            stop_loss_bps=row.get("stop_loss_bps"),
            take_profit_bps=row.get("take_profit_bps"),
            trailing_stop_bps=row.get("trailing_stop_bps"),
            partial_take_profit_bps=row.get("partial_take_profit_bps"),
            partial_exit_fraction=row.get("partial_exit_fraction"),
            min_holding_minutes=row.get("min_holding_minutes"),
            exit_on_opposite_signal=bool(row.get("exit_on_opposite_signal")),
            exit_on_close_signal=bool(row.get("exit_on_close_signal")),
            exit_on_reduce_signal=bool(row.get("exit_on_reduce_signal")),
            reduce_fraction=row.get("reduce_fraction"),
            exit_on_add_signal=bool(row.get("exit_on_add_signal")),
            add_fraction=row.get("add_fraction"),
            exit_on_rebalance_signal=bool(row.get("exit_on_rebalance_signal")),
            rebalance_target_fraction=row.get("rebalance_target_fraction"),
            bracket_type=row.get("bracket_type") or "none",
            bracket_time_stop_minutes=row.get("bracket_time_stop_minutes"),
            bracket_break_even_after_bps=row.get("bracket_break_even_after_bps"),
            entry_order_type=row.get("entry_order_type") or "market",
            entry_limit_offset_bps=row.get("entry_limit_offset_bps"),
            entry_stop_offset_bps=row.get("entry_stop_offset_bps"),
            entry_timeout_minutes=row.get("entry_timeout_minutes"),
            entry_time_in_force=row.get("entry_time_in_force") or "gtc",
            entry_post_only=bool(row.get("entry_post_only")),
            slippage_bps=row.get("slippage_bps") or 0.0,
            max_fill_fraction=row.get("max_fill_fraction") or 1.0,
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
            min_fee_edge_bps=row.get("min_fee_edge_bps"),
            fee_edge_bps=row.get("fee_edge_bps"),
            position_weight=row.get("position_weight"),
            notional_usd=row.get("notional_usd"),
            reason_codes=list(row.get("reason_codes") or []),
            block_reasons=list(row.get("block_reasons") or []),
        )
        key = (signal.execution_venue, signal.execution_symbol, signal.real_market_symbol)
        if key not in allowed_bindings:
            raise ValueError(
                "StrategySignalRecord has no matching SymbolBinding: "
                f"{signal.execution_venue}/{signal.execution_symbol}/{signal.real_market_symbol}"
            )
        records.append(signal.model_dump(mode="python"))

    return pl.DataFrame(records)
