from __future__ import annotations

from collections import Counter
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json

import polars as pl

from sis.backtest.costs import CostProfile, load_cost_profiles, round_trip_cost_bps
from sis.backtest.signals import ResearchSignal, load_research_signals
from sis.core.context import DecisionContext
from sis.core.decision import DecisionRecord
from sis.core.execution_plan import build_execution_plan
from sis.core.strategy import SignalPassthroughStrategy
from sis.risk.risk_gate import evaluate_risk_gate
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_state_comparison_summary,
    phase_gate_flat_fields,
    normalize_phase_gate_summary,
    readiness_flat_fields,
    normalize_readiness_summary,
    latest_execution_lineage_fields_from_payload,
    latest_execution_sections,
)


@dataclass(frozen=True)
class BacktestMetrics:
    venue: str
    canonical_symbol: str
    total_return: float
    annual_return: float | None
    max_drawdown: float
    sharpe: float | None
    win_rate: float | None
    profit_factor: float | None
    trade_count: int
    avg_trade_return: float | None
    worst_trade: float | None
    exposure_ratio: float
    cost_drag_bps: float
    cost_source: str | None
    stale_rejected_count: int
    halt_rejected_count: int


def _parse_quote_ts(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported quote timestamp: {value!r}")


def _float_from_summary_value(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return 0.0


def _execution_price(row: dict, side: str = "long") -> float | None:
    if side == "short":
        for key in ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    for key in ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price"):
        value = row.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
    return None


def _exit_price(row: dict, side: str = "long") -> float | None:
    if side == "short":
        for key in ("exec_buy_price", "mark_price", "mid_price", "oracle_price", "index_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value)
        return None
    for key in ("exec_sell_price", "mark_price", "mid_price", "oracle_price", "index_price"):
        value = row.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
    return None


def _net_return(entry_price: float, exit_price: float, side: str, cost_bps: float) -> float:
    gross = exit_price / entry_price - 1.0
    if side == "short":
        gross = entry_price / exit_price - 1.0
    return gross - cost_bps / 10_000


def _gross_return_bps(entry_price: float, exit_price: float, side: str) -> float:
    gross = exit_price / entry_price - 1.0
    if side == "short":
        gross = entry_price / exit_price - 1.0
    return gross * 10_000


def _entry_fill_index(
    *,
    rows: list[dict],
    quote_times: list[datetime],
    reference_index: int,
    signal: ResearchSignal,
) -> tuple[int | None, str | None]:
    order_type = signal.entry_order_type
    if order_type == "market":
        return reference_index, None
    reference_price = _execution_price(rows[reference_index], signal.side)
    if reference_price is None:
        return None, "entry_order_unfilled"
    timeout_at = None
    if signal.entry_timeout_minutes is not None:
        timeout_at = quote_times[reference_index] + timedelta(minutes=signal.entry_timeout_minutes)
    if order_type == "limit":
        offset = signal.entry_limit_offset_bps
        if offset is None:
            return None, "entry_order_unfilled"
        if signal.side == "short":
            trigger_price = reference_price * (1.0 + offset / 10_000)
            comparison = "gte"
        else:
            trigger_price = reference_price * (1.0 - offset / 10_000)
            comparison = "lte"
    elif order_type == "stop_market":
        offset = signal.entry_stop_offset_bps
        if offset is None:
            return None, "entry_order_unfilled"
        if signal.side == "short":
            trigger_price = reference_price * (1.0 - offset / 10_000)
            comparison = "lte"
        else:
            trigger_price = reference_price * (1.0 + offset / 10_000)
            comparison = "gte"
    else:
        raise ValueError(f"Unsupported entry_order_type: {order_type}")

    search_end = reference_index + 1 if signal.entry_time_in_force in {"ioc", "fok"} else len(rows)
    for index in range(reference_index, search_end):
        if timeout_at is not None and quote_times[index] > timeout_at:
            return None, "entry_order_unfilled"
        price = _execution_price(rows[index], signal.side)
        if price is not None and (
            price >= trigger_price if comparison == "gte" else price <= trigger_price
        ):
            if signal.entry_post_only and index == reference_index:
                return None, "entry_order_post_only_would_cross"
            return index, None
    return None, "entry_order_unfilled"


def _risk_exit_index(
    *,
    rows: list[dict],
    entry_index: int,
    horizon_exit_index: int,
    entry_price: float,
    side: str,
    stop_loss_bps: float | None,
    take_profit_bps: float | None,
) -> tuple[int, str]:
    if stop_loss_bps is None and take_profit_bps is None:
        return horizon_exit_index, "fixed_horizon"
    for index in range(entry_index + 1, horizon_exit_index + 1):
        exit_price = _exit_price(rows[index], side)
        if exit_price is None:
            continue
        gross_bps = _gross_return_bps(entry_price, exit_price, side)
        if stop_loss_bps is not None and gross_bps <= -stop_loss_bps:
            return index, "stop_loss"
        if take_profit_bps is not None and gross_bps >= take_profit_bps:
            return index, "take_profit"
    return horizon_exit_index, "fixed_horizon"


def _scaled_signal_return(
    *,
    rows: list[dict],
    quote_times: list[datetime],
    entry_index: int,
    horizon_exit_index: int,
    entry_price: float,
    side: str,
    cost_bps: float,
    signal: ResearchSignal,
    final_exit_reason: str = "fixed_horizon",
    min_exit_index: int | None = None,
    microstructure_fill_fraction: float = 1.0,
    reduce_events: list[tuple[int, float]] | None = None,
    add_events: list[tuple[int, float]] | None = None,
    rebalance_events: list[tuple[int, float, float | None]] | None = None,
) -> tuple[float, str]:
    open_legs: list[tuple[float, float]] = [(entry_price, 1.0)]
    exit_legs: list[tuple[float, float, float, str]] = []
    marker_reasons: list[str] = []
    best_bps = 0.0
    partial_done = False
    final_reason = final_exit_reason
    break_even_armed = False
    bracket_enabled = signal.bracket_type == "oco"
    exit_priority = tuple(
        item.strip() for item in str(signal.exit_priority or "").split(",") if item.strip()
    ) or (
        "break_even_stop",
        "stop_loss",
        "partial_take_profit",
        "take_profit",
        "trailing_stop",
        "time_stop",
    )
    time_stop_at = (
        quote_times[entry_index] + timedelta(minutes=signal.bracket_time_stop_minutes)
        if bracket_enabled and signal.bracket_time_stop_minutes is not None
        else None
    )
    adjustment_events_by_index: dict[int, list[tuple[str, float, float | None]]] = {}
    for index, fraction in reduce_events or []:
        adjustment_events_by_index.setdefault(index, []).append(("reduce", fraction, None))
    for index, fraction in add_events or []:
        adjustment_events_by_index.setdefault(index, []).append(("add", fraction, None))
    for index, target_fraction, min_delta_fraction in rebalance_events or []:
        adjustment_events_by_index.setdefault(index, []).append(
            ("rebalance", target_fraction, min_delta_fraction)
        )

    def open_fraction() -> float:
        return sum(fraction for _leg_entry_price, fraction in open_legs)

    def close_open_fraction(exit_price: float, fraction: float, reason: str) -> None:
        nonlocal open_legs
        to_close = max(fraction, 0.0)
        updated_legs: list[tuple[float, float]] = []
        for leg_entry_price, leg_fraction in open_legs:
            if to_close <= 0:
                updated_legs.append((leg_entry_price, leg_fraction))
                continue
            leg_close_fraction = min(leg_fraction, to_close)
            if leg_close_fraction > 0:
                exit_legs.append((leg_entry_price, exit_price, leg_close_fraction, reason))
                to_close -= leg_close_fraction
            remaining_leg_fraction = leg_fraction - leg_close_fraction
            if remaining_leg_fraction > 0:
                updated_legs.append((leg_entry_price, remaining_leg_fraction))
        open_legs = updated_legs

    def close_all(exit_price: float, reason: str) -> None:
        close_open_fraction(exit_price, open_fraction(), reason)

    for index in range(entry_index + 1, horizon_exit_index + 1):
        exit_price = _exit_price(rows[index], side)
        if exit_price is None:
            continue
        exit_allowed = min_exit_index is None or index >= min_exit_index
        gross_bps = _gross_return_bps(entry_price, exit_price, side)
        best_bps = max(best_bps, gross_bps)
        for event_type, value, min_delta in (
            adjustment_events_by_index.get(index, []) if exit_allowed else []
        ):
            current_open = open_fraction()
            if current_open <= 0:
                break
            if event_type == "reduce":
                fraction = min(max(value, 0.0), 1.0) * current_open
                if fraction > 0:
                    close_open_fraction(exit_price, fraction, "reduce_signal")
            elif event_type == "add":
                add_entry_price = _execution_price(rows[index], side)
                if add_entry_price is not None:
                    add_fraction = max(value, 0.0)
                    if add_fraction > 0:
                        open_legs.append((add_entry_price, add_fraction))
                        marker_reasons.append("add_signal")
            else:
                target = max(value, 0.0)
                if min_delta is not None and abs(target - current_open) < min_delta:
                    marker_reasons.append("rebalance_band_skip")
                    continue
                marker_reasons.append("rebalance_signal")
                if target < current_open:
                    close_open_fraction(exit_price, current_open - target, "rebalance_signal")
                elif target > current_open:
                    rebalance_entry_price = _execution_price(rows[index], side)
                    if rebalance_entry_price is not None:
                        open_legs.append((rebalance_entry_price, target - current_open))
            if open_fraction() <= 0:
                final_reason = f"{event_type}_signal"
                break
        if open_fraction() <= 0:
            break
        if (
            bracket_enabled
            and signal.bracket_break_even_after_bps is not None
            and gross_bps >= signal.bracket_break_even_after_bps
        ):
            break_even_armed = True
        if exit_allowed:
            for exit_rule in exit_priority:
                if (
                    exit_rule == "break_even_stop"
                    and bracket_enabled
                    and break_even_armed
                    and gross_bps <= 0
                ):
                    close_all(exit_price, "bracket_break_even_stop")
                    final_reason = "bracket_break_even_stop"
                    break
                if (
                    exit_rule == "stop_loss"
                    and signal.stop_loss_bps is not None
                    and gross_bps <= -signal.stop_loss_bps
                ):
                    final_reason = "bracket_stop_loss" if bracket_enabled else "stop_loss"
                    close_all(exit_price, final_reason)
                    break
                if (
                    exit_rule == "partial_take_profit"
                    and signal.partial_take_profit_bps is not None
                    and signal.partial_exit_fraction is not None
                    and not partial_done
                    and gross_bps >= signal.partial_take_profit_bps
                ):
                    fraction = min(max(signal.partial_exit_fraction, 0.0), open_fraction())
                    if fraction > 0:
                        close_open_fraction(exit_price, fraction, "partial_take_profit")
                        partial_done = True
                        if bracket_enabled and signal.bracket_break_even_after_partial_take_profit:
                            break_even_armed = True
                        if open_fraction() <= 0:
                            final_reason = "partial_take_profit"
                            break
                if (
                    exit_rule == "take_profit"
                    and signal.take_profit_bps is not None
                    and gross_bps >= signal.take_profit_bps
                ):
                    final_reason = "bracket_take_profit" if bracket_enabled else "take_profit"
                    close_all(exit_price, final_reason)
                    break
                if (
                    exit_rule == "trailing_stop"
                    and signal.trailing_stop_bps is not None
                    and best_bps > 0
                    and (
                        signal.trailing_stop_activation_bps is None
                        or best_bps >= signal.trailing_stop_activation_bps
                    )
                    and gross_bps <= best_bps - signal.trailing_stop_bps
                ):
                    close_all(exit_price, "trailing_stop")
                    final_reason = "trailing_stop"
                    break
                if (
                    exit_rule == "time_stop"
                    and time_stop_at is not None
                    and quote_times[index] >= time_stop_at
                ):
                    close_all(exit_price, "bracket_time_stop")
                    final_reason = "bracket_time_stop"
                    break
            if open_fraction() <= 0:
                break

    if open_fraction() > 0:
        horizon_price = _exit_price(rows[horizon_exit_index], side)
        if horizon_price is None:
            return 0.0, "missing_exit_price"
        close_all(horizon_price, final_reason)

    gross_return = sum(
        (
            exit_price / leg_entry_price - 1.0
            if side != "short"
            else leg_entry_price / exit_price - 1.0
        )
        * fraction
        for leg_entry_price, exit_price, fraction, _reason in exit_legs
    )
    reason = "+".join(
        dict.fromkeys(
            [
                *marker_reasons,
                *(reason for _leg_entry_price, _exit_price, _fraction, reason in exit_legs),
            ]
        )
    )
    fill_fraction = _effective_fill_fraction(signal, microstructure_fill_fraction)
    execution_cost_bps = cost_bps + signal.slippage_bps
    return (
        gross_return - execution_cost_bps / 10_000
    ) * signal.position_weight * fill_fraction, reason


def _effective_fill_fraction(signal: ResearchSignal, microstructure_fill_fraction: float) -> float:
    return min(max(signal.max_fill_fraction, 0.0), 1.0) * min(
        max(microstructure_fill_fraction, 0.0), 1.0
    )


def _microstructure_fill_fraction(
    signal: ResearchSignal, entry: dict
) -> tuple[float | None, str | None]:
    if signal.max_latency_ms is not None:
        if signal.latency_ms is None:
            return None, "microstructure_latency_missing"
        if signal.latency_ms > signal.max_latency_ms:
            return None, "microstructure_latency_too_high"
    if signal.min_queue_position_score is not None:
        if signal.queue_position_score is None:
            return None, "microstructure_queue_position_missing"
        if signal.queue_position_score < signal.min_queue_position_score:
            return None, "microstructure_queue_position_too_low"
    if signal.side == "short" and signal.min_borrow_availability_ratio is not None:
        if signal.borrow_availability_ratio is None:
            return None, "short_borrow_availability_missing"
        if signal.borrow_availability_ratio < signal.min_borrow_availability_ratio:
            return None, "short_borrow_availability_too_low"
    if signal.side == "short" and signal.max_borrow_cost_bps is not None:
        if signal.borrow_cost_bps is None:
            return None, "short_borrow_cost_missing"
        if signal.borrow_cost_bps > signal.max_borrow_cost_bps:
            return None, "short_borrow_cost_too_high"
    if signal.max_tax_drag_bps is not None:
        if signal.tax_drag_bps is None:
            return None, "tax_drag_missing"
        if signal.tax_drag_bps > signal.max_tax_drag_bps:
            return None, "tax_drag_too_high"
    if signal.max_turnover_pressure is not None:
        if signal.turnover_pressure is None:
            return None, "turnover_pressure_missing"
        if signal.turnover_pressure > signal.max_turnover_pressure:
            return None, "turnover_pressure_too_high"
    if signal.max_capacity_usage_ratio is not None:
        if signal.capacity_usage_ratio is None:
            return None, "capacity_usage_missing"
        if signal.capacity_usage_ratio > signal.max_capacity_usage_ratio:
            return None, "capacity_usage_too_high"
    if signal.max_correlation_crowding_score is not None:
        if signal.correlation_crowding_score is None:
            return None, "correlation_crowding_missing"
        if signal.correlation_crowding_score > signal.max_correlation_crowding_score:
            return None, "correlation_crowding_too_high"
    if signal.min_fee_edge_bps is not None:
        if signal.fee_edge_bps is None:
            return None, "fee_edge_missing"
        if signal.fee_edge_bps < signal.min_fee_edge_bps:
            return None, "fee_edge_too_low"
    spread = entry.get("spread_bps")
    if (
        signal.max_spread_bps is not None
        and isinstance(spread, int | float)
        and float(spread) > signal.max_spread_bps
    ):
        return None, "microstructure_spread_too_wide"
    if signal.min_depth_usd is None:
        return 1.0, None
    depth_column = signal.depth_column or "min_side_depth_10bps_usd"
    depth = entry.get(depth_column)
    if not isinstance(depth, int | float):
        return None, "microstructure_depth_missing"
    if float(depth) < signal.min_depth_usd:
        return None, "microstructure_depth_too_low"
    if signal.notional_usd is None or signal.notional_usd <= 0:
        return 1.0, None
    available = float(depth) * min(max(signal.depth_participation_rate, 0.0), 1.0)
    return min(1.0, available / signal.notional_usd), None


def _max_drawdown(equity: list[float]) -> float:
    peak = 1.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return worst


def _dominant_cost_source(cost_sources: list[str]) -> str | None:
    if not cost_sources:
        return None
    return max(set(cost_sources), key=cost_sources.count)


def _metrics_for_group(
    group: pl.DataFrame,
    cost_profiles: dict[tuple[str, str], CostProfile] | None = None,
) -> BacktestMetrics:
    rows = group.sort("ts_client").to_dicts()
    venue = str(rows[0]["venue"])
    symbol = str(rows[0]["canonical_symbol"])
    returns: list[float] = []
    equity = [1.0]
    cost_drag_bps = 0.0
    cost_sources: list[str] = []
    stale_rejected = 0
    halt_rejected = 0
    candidate_count = max(len(rows) - 1, 0)

    for entry, exit_ in zip(rows, rows[1:], strict=False):
        if entry.get("oracle_ts_ms") is None:
            stale_rejected += 1
        if entry.get("market_status") != "open" or entry.get("is_tradable") is not True:
            halt_rejected += 1
            continue

        entry_price = _execution_price(entry)
        exit_price = _exit_price(exit_)
        if entry_price is None or exit_price is None:
            stale_rejected += 1
            continue

        spread_raw = entry.get("spread_bps")
        spread = float(spread_raw) if isinstance(spread_raw, int | float) else None
        cost_bps, cost_source = round_trip_cost_bps(
            venue=venue,
            symbol=symbol,
            holding_horizon="4h",
            quote_spread_bps=spread,
            cost_profiles=cost_profiles or {},
        )
        net = _net_return(entry_price, exit_price, "long", cost_bps)
        returns.append(net)
        cost_drag_bps += cost_bps
        cost_sources.append(cost_source)
        equity.append(equity[-1] * (1.0 + net))

    total_return = equity[-1] - 1.0
    average = sum(returns) / len(returns) if returns else None
    variance = (
        sum((item - average) ** 2 for item in returns) / len(returns)
        if returns and average is not None
        else None
    )
    sharpe = (
        average / math.sqrt(variance) * math.sqrt(252)
        if average is not None and variance and variance > 0
        else None
    )
    wins = [item for item in returns if item > 0]
    losses = [item for item in returns if item < 0]
    profit_factor = sum(wins) / abs(sum(losses)) if losses else (None if not wins else float("inf"))
    exposure_ratio = len(returns) / candidate_count if candidate_count else 0.0

    return BacktestMetrics(
        venue=venue,
        canonical_symbol=symbol,
        total_return=total_return,
        annual_return=None,
        max_drawdown=_max_drawdown(equity),
        sharpe=sharpe,
        win_rate=len(wins) / len(returns) if returns else None,
        profit_factor=profit_factor,
        trade_count=len(returns),
        avg_trade_return=average,
        worst_trade=min(returns) if returns else None,
        exposure_ratio=exposure_ratio,
        cost_drag_bps=cost_drag_bps,
        cost_source=_dominant_cost_source(cost_sources),
        stale_rejected_count=stale_rejected,
        halt_rejected_count=halt_rejected,
    )


def _metrics_from_returns(
    *,
    venue: str,
    symbol: str,
    returns: list[float],
    equity: list[float],
    cost_drag_bps: float,
    cost_source: str | None,
    stale_rejected: int,
    halt_rejected: int,
    candidate_count: int,
) -> BacktestMetrics:
    total_return = equity[-1] - 1.0
    average = sum(returns) / len(returns) if returns else None
    variance = (
        sum((item - average) ** 2 for item in returns) / len(returns)
        if returns and average is not None
        else None
    )
    sharpe = (
        average / math.sqrt(variance) * math.sqrt(252)
        if average is not None and variance and variance > 0
        else None
    )
    wins = [item for item in returns if item > 0]
    losses = [item for item in returns if item < 0]
    profit_factor = sum(wins) / abs(sum(losses)) if losses else (None if not wins else float("inf"))
    exposure_ratio = len(returns) / candidate_count if candidate_count else 0.0

    return BacktestMetrics(
        venue=venue,
        canonical_symbol=symbol,
        total_return=total_return,
        annual_return=None,
        max_drawdown=_max_drawdown(equity),
        sharpe=sharpe,
        win_rate=len(wins) / len(returns) if returns else None,
        profit_factor=profit_factor,
        trade_count=len(returns),
        avg_trade_return=average,
        worst_trade=min(returns) if returns else None,
        exposure_ratio=exposure_ratio,
        cost_drag_bps=cost_drag_bps,
        cost_source=cost_source,
        stale_rejected_count=stale_rejected,
        halt_rejected_count=halt_rejected,
    )


def _metrics_for_signals(
    quotes: pl.DataFrame,
    signals: list[ResearchSignal],
    cost_profiles: dict[tuple[str, str], CostProfile] | None = None,
    *,
    exit_model: str = "next_row",
    holding_horizon_minutes: int | None = None,
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    if exit_model not in {"next_row", "fixed_horizon"}:
        raise ValueError(f"Unsupported exit_model: {exit_model}")
    if exit_model == "fixed_horizon" and (
        holding_horizon_minutes is None or holding_horizon_minutes <= 0
    ):
        raise ValueError("holding_horizon_minutes must be positive for fixed_horizon")
    rows_by_key: dict[tuple[str, str], list[dict]] = {}
    for row in quotes.sort("ts_client").to_dicts():
        key = (str(row["venue"]), str(row["canonical_symbol"]).upper())
        rows_by_key.setdefault(key, []).append(row)

    signals_by_symbol: dict[str, list[ResearchSignal]] = {}
    for signal in signals:
        signals_by_symbol.setdefault(signal.canonical_symbol, []).append(signal)
    signals_by_symbol = {
        symbol: sorted(symbol_signals, key=lambda item: item.ts_signal)
        for symbol, symbol_signals in signals_by_symbol.items()
    }

    metrics: list[BacktestMetrics] = []
    decision_records: list[DecisionRecord] = []
    blocked_reason_counts: dict[str, int] = {}
    exit_reason_counts: dict[str, int] = {}
    entry_order_type_counts: dict[str, int] = {}
    executed_signal_results: list[dict[str, object]] = []
    entry_order_unfilled = 0
    executed = 0
    blocked = 0
    strategy = SignalPassthroughStrategy()
    for (venue, symbol), rows in rows_by_key.items():
        symbol_signals = signals_by_symbol.get(symbol, [])
        if not symbol_signals:
            continue

        returns: list[float] = []
        equity = [1.0]
        cost_drag_bps = 0.0
        cost_sources: list[str] = []
        stale_rejected = 0
        halt_rejected = 0
        quote_times = [_parse_quote_ts(row["ts_client"]) for row in rows]

        for signal in symbol_signals:
            if signal.side in {"close", "reduce", "add", "rebalance"}:
                continue
            reference_index = next(
                (
                    index
                    for index, quote_time in enumerate(quote_times)
                    if quote_time >= signal.ts_signal
                ),
                None,
            )
            if reference_index is None:
                stale_rejected += 1
                continue
            entry_index, entry_block_reason = _entry_fill_index(
                rows=rows,
                quote_times=quote_times,
                reference_index=reference_index,
                signal=signal,
            )
            if entry_index is None:
                entry_order_unfilled += 1
                reason = entry_block_reason or "entry_order_unfilled"
                blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
                continue
            entry_order_type_counts[signal.entry_order_type] = (
                entry_order_type_counts.get(signal.entry_order_type, 0) + 1
            )
            if exit_model == "fixed_horizon":
                target_exit_ts = quote_times[entry_index] + timedelta(
                    minutes=holding_horizon_minutes or 0
                )
                exit_index = next(
                    (
                        index
                        for index, quote_time in enumerate(
                            quote_times[entry_index + 1 :], start=entry_index + 1
                        )
                        if quote_time >= target_exit_ts
                    ),
                    None,
                )
            else:
                exit_index = entry_index + 1 if entry_index + 1 < len(rows) else None
            final_exit_reason = "fixed_horizon" if exit_model == "fixed_horizon" else "next_row"
            if exit_index is None:
                stale_rejected += 1
                continue
            min_exit_index = None
            if signal.min_holding_minutes is not None:
                min_exit_ts = quote_times[entry_index] + timedelta(
                    minutes=signal.min_holding_minutes
                )
                min_exit_index = next(
                    (
                        index
                        for index, quote_time in enumerate(
                            quote_times[entry_index + 1 :], start=entry_index + 1
                        )
                        if quote_time >= min_exit_ts
                    ),
                    None,
                )
                if min_exit_index is None:
                    stale_rejected += 1
                    continue
                exit_index = max(exit_index, min_exit_index)
            if signal.max_holding_minutes is not None:
                max_exit_ts = quote_times[entry_index] + timedelta(
                    minutes=signal.max_holding_minutes
                )
                max_exit_index = next(
                    (
                        index
                        for index, quote_time in enumerate(
                            quote_times[entry_index + 1 :], start=entry_index + 1
                        )
                        if quote_time >= max_exit_ts
                    ),
                    None,
                )
                if max_exit_index is None:
                    stale_rejected += 1
                    continue
                if min_exit_index is not None and max_exit_index < min_exit_index:
                    max_exit_index = min_exit_index
                if max_exit_index < exit_index:
                    exit_index = max_exit_index
                    final_exit_reason = "max_holding_time"
            if signal.exit_on_close_signal:
                close_signal = next(
                    (
                        item
                        for item in symbol_signals
                        if item.ts_signal > signal.ts_signal
                        and item.side == "close"
                        and (
                            signal.min_holding_minutes is None
                            or item.ts_signal
                            >= quote_times[entry_index]
                            + timedelta(minutes=signal.min_holding_minutes)
                        )
                    ),
                    None,
                )
                if close_signal is not None:
                    close_exit_index = next(
                        (
                            index
                            for index, quote_time in enumerate(
                                quote_times[entry_index + 1 :], start=entry_index + 1
                            )
                            if quote_time >= close_signal.ts_signal
                        ),
                        None,
                    )
                    if close_exit_index is not None and close_exit_index < exit_index:
                        exit_index = close_exit_index
                        final_exit_reason = "close_signal"
            reduce_events: list[tuple[int, float]] = []
            if signal.exit_on_reduce_signal:
                for reduce_signal in (
                    item
                    for item in symbol_signals
                    if item.ts_signal > signal.ts_signal
                    and item.side == "reduce"
                    and (
                        signal.min_holding_minutes is None
                        or item.ts_signal
                        >= quote_times[entry_index] + timedelta(minutes=signal.min_holding_minutes)
                    )
                ):
                    reduce_index = next(
                        (
                            index
                            for index, quote_time in enumerate(
                                quote_times[entry_index + 1 :], start=entry_index + 1
                            )
                            if quote_time >= reduce_signal.ts_signal
                        ),
                        None,
                    )
                    if reduce_index is not None and reduce_index < exit_index:
                        reduce_events.append((reduce_index, reduce_signal.reduce_fraction or 1.0))
            add_events: list[tuple[int, float]] = []
            if signal.exit_on_add_signal:
                for add_signal in (
                    item
                    for item in symbol_signals
                    if item.ts_signal > signal.ts_signal
                    and item.side == "add"
                    and (
                        signal.min_holding_minutes is None
                        or item.ts_signal
                        >= quote_times[entry_index] + timedelta(minutes=signal.min_holding_minutes)
                    )
                ):
                    add_index = next(
                        (
                            index
                            for index, quote_time in enumerate(
                                quote_times[entry_index + 1 :], start=entry_index + 1
                            )
                            if quote_time >= add_signal.ts_signal
                        ),
                        None,
                    )
                    if add_index is not None and add_index < exit_index:
                        add_events.append((add_index, add_signal.add_fraction or 1.0))
            rebalance_events: list[tuple[int, float, float | None]] = []
            if signal.exit_on_rebalance_signal:
                for rebalance_signal in (
                    item
                    for item in symbol_signals
                    if item.ts_signal > signal.ts_signal
                    and item.side == "rebalance"
                    and (
                        signal.min_holding_minutes is None
                        or item.ts_signal
                        >= quote_times[entry_index] + timedelta(minutes=signal.min_holding_minutes)
                    )
                ):
                    rebalance_index = next(
                        (
                            index
                            for index, quote_time in enumerate(
                                quote_times[entry_index + 1 :], start=entry_index + 1
                            )
                            if quote_time >= rebalance_signal.ts_signal
                        ),
                        None,
                    )
                    if rebalance_index is not None and rebalance_index < exit_index:
                        rebalance_events.append(
                            (
                                rebalance_index,
                                rebalance_signal.rebalance_target_fraction or 0.0,
                                rebalance_signal.rebalance_min_delta_fraction,
                            )
                        )
            if signal.exit_on_opposite_signal:
                opposite_signal = next(
                    (
                        item
                        for item in symbol_signals
                        if item.ts_signal > signal.ts_signal
                        and item.side in {"long", "short"}
                        and item.side != signal.side
                        and (
                            signal.min_holding_minutes is None
                            or item.ts_signal
                            >= quote_times[entry_index]
                            + timedelta(minutes=signal.min_holding_minutes)
                        )
                    ),
                    None,
                )
                if opposite_signal is not None:
                    opposite_exit_index = next(
                        (
                            index
                            for index, quote_time in enumerate(
                                quote_times[entry_index + 1 :], start=entry_index + 1
                            )
                            if quote_time >= opposite_signal.ts_signal
                        ),
                        None,
                    )
                    if opposite_exit_index is not None and opposite_exit_index < exit_index:
                        exit_index = opposite_exit_index
                        final_exit_reason = "opposite_signal"

            entry = rows[entry_index]
            context = DecisionContext(
                decision_ts=signal.ts_signal,
                venue=venue,
                canonical_symbol=symbol,
                timeframe=signal.timeframe,
                quote_ts=_parse_quote_ts(entry["ts_client"]),
                signal_ts=signal.ts_signal,
                signal_side=signal.side,
                signal_strength=signal.signal_strength,
                strategy_name="signal_passthrough_strategy",
                market_status=str(entry.get("market_status", "unknown")),
                is_tradable=bool(entry.get("is_tradable")),
            )
            strategy_decision = strategy.evaluate(context)
            risk_decision = evaluate_risk_gate(context, entry)
            execution_plan = build_execution_plan(context, strategy_decision, risk_decision)
            decision_records.append(
                DecisionRecord(
                    context=context,
                    strategy_decision=strategy_decision,
                    risk_decision=risk_decision,
                    execution_plan=execution_plan.model_dump(mode="json"),
                )
            )
            if not risk_decision.allowed:
                blocked += 1
                for reason in risk_decision.blocked_reasons:
                    blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
                if risk_decision.stale_rejected:
                    stale_rejected += 1
                if risk_decision.halt_rejected:
                    halt_rejected += 1
                continue

            entry_price = _execution_price(entry, signal.side)
            if entry_price is None:
                stale_rejected += 1
                continue
            microstructure_fill_fraction, microstructure_block_reason = (
                _microstructure_fill_fraction(signal, entry)
            )
            if microstructure_block_reason is not None:
                blocked += 1
                blocked_reason_counts[microstructure_block_reason] = (
                    blocked_reason_counts.get(microstructure_block_reason, 0) + 1
                )
                continue
            effective_fill_fraction = _effective_fill_fraction(
                signal, microstructure_fill_fraction or 1.0
            )
            if (
                signal.min_fill_fraction is not None
                and effective_fill_fraction < signal.min_fill_fraction
            ):
                blocked += 1
                blocked_reason_counts["execution_fill_fraction_too_low"] = (
                    blocked_reason_counts.get("execution_fill_fraction_too_low", 0) + 1
                )
                continue
            spread_raw = entry.get("spread_bps")
            spread = float(spread_raw) if isinstance(spread_raw, int | float) else None
            cost_bps, cost_source = round_trip_cost_bps(
                venue=venue,
                symbol=symbol,
                holding_horizon=signal.timeframe,
                quote_spread_bps=spread,
                cost_profiles=cost_profiles or {},
            )
            signal_return, exit_reason = _scaled_signal_return(
                rows=rows,
                quote_times=quote_times,
                entry_index=entry_index,
                horizon_exit_index=exit_index,
                entry_price=entry_price,
                side=signal.side,
                cost_bps=cost_bps,
                signal=signal,
                final_exit_reason=final_exit_reason,
                min_exit_index=min_exit_index,
                microstructure_fill_fraction=microstructure_fill_fraction or 1.0,
                reduce_events=reduce_events,
                add_events=add_events,
                rebalance_events=rebalance_events,
            )
            if exit_reason == "missing_exit_price":
                stale_rejected += 1
                continue
            returns.append(signal_return)
            exit_reason_counts[exit_reason] = exit_reason_counts.get(exit_reason, 0) + 1
            cost_drag_bps += cost_bps + signal.slippage_bps
            cost_sources.append(cost_source)
            equity.append(equity[-1] * (1.0 + returns[-1]))
            executed += 1
            executed_signal_results.append(
                {
                    "signal_id": signal.signal_id,
                    "ts_signal": signal.ts_signal,
                    "venue": venue,
                    "canonical_symbol": symbol,
                    "side": signal.side,
                    "timeframe": signal.timeframe,
                    "signal_return": signal_return,
                    "exit_reason": exit_reason,
                    "cost_drag_bps": cost_bps + signal.slippage_bps,
                    "position_weight": signal.position_weight,
                    "notional_usd": signal.notional_usd,
                    "multi_leg_group_id": signal.multi_leg_group_id,
                    "multi_leg_leg_index": signal.multi_leg_leg_index,
                    "multi_leg_leg_count": signal.multi_leg_leg_count,
                    "multi_leg_anchor_real_market_symbol": (
                        signal.multi_leg_anchor_real_market_symbol
                    ),
                }
            )

        metrics.append(
            _metrics_from_returns(
                venue=venue,
                symbol=symbol,
                returns=returns,
                equity=equity,
                cost_drag_bps=cost_drag_bps,
                cost_source=_dominant_cost_source(cost_sources),
                stale_rejected=stale_rejected,
                halt_rejected=halt_rejected,
                candidate_count=len(symbol_signals),
            )
        )
    summary = {
        "mode": "signal_driven",
        "exit_model": exit_model,
        "holding_horizon_minutes": holding_horizon_minutes,
        "signals_considered": len(signals),
        "executed_count": executed,
        "blocked_count": blocked,
        "blocked_reason_counts": blocked_reason_counts,
        "exit_reason_counts": exit_reason_counts,
        "entry_order_type_counts": entry_order_type_counts,
        "entry_order_unfilled_count": entry_order_unfilled,
        "executed_signal_results": executed_signal_results,
        "executed_signal_summary": _executed_signal_summary(executed_signal_results),
        "records_written": len(decision_records),
    }
    return metrics, decision_records, summary


def _executed_signal_summary(results: list[dict[str, object]]) -> dict[str, object]:
    if not results:
        return {
            "result_count": 0,
            "first_ts_signal": None,
            "last_ts_signal": None,
            "side_counts": {},
            "symbol_counts": {},
            "timeframe_counts": {},
            "exit_reason_counts": {},
            "total_signal_return": 0.0,
            "avg_signal_return": None,
            "win_rate": None,
            "total_cost_drag_bps": 0.0,
            "total_notional_usd": 0.0,
            "notional_weighted_signal_return": None,
        }

    signal_returns = [
        _float_from_summary_value(item.get("signal_return") or 0.0) for item in results
    ]
    notionals = [_float_from_summary_value(item.get("notional_usd") or 0.0) for item in results]
    total_notional = sum(notionals)
    total_signal_return = sum(signal_returns)
    ts_values = [str(item.get("ts_signal")) for item in results if item.get("ts_signal")]
    return {
        "result_count": len(results),
        "first_ts_signal": min(ts_values) if ts_values else None,
        "last_ts_signal": max(ts_values) if ts_values else None,
        "side_counts": dict(Counter(str(item.get("side")) for item in results)),
        "symbol_counts": dict(Counter(str(item.get("canonical_symbol")) for item in results)),
        "timeframe_counts": dict(Counter(str(item.get("timeframe")) for item in results)),
        "exit_reason_counts": dict(Counter(str(item.get("exit_reason")) for item in results)),
        "total_signal_return": total_signal_return,
        "avg_signal_return": total_signal_return / len(signal_returns),
        "win_rate": sum(1 for value in signal_returns if value > 0) / len(signal_returns),
        "total_cost_drag_bps": sum(
            _float_from_summary_value(item.get("cost_drag_bps") or 0.0) for item in results
        ),
        "total_notional_usd": total_notional,
        "notional_weighted_signal_return": (
            sum(
                signal_return * notional
                for signal_return, notional in zip(signal_returns, notionals, strict=True)
            )
            / total_notional
            if total_notional > 0
            else None
        ),
    }


def _write_decision_records(records: list[DecisionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def _write_decision_summary(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def run_backtest_bridge_with_decisions(
    quotes_path: Path,
    signals_path: Path | None = None,
    cost_matrix_path: Path | None = None,
    exit_model: str = "next_row",
    holding_horizon_minutes: int | None = None,
    decision_log_path: Path | None = None,
    decision_summary_path: Path | None = None,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    if not quotes_path.exists():
        raise FileNotFoundError(f"Normalized quote parquet not found: {quotes_path}")
    quotes = pl.read_parquet(quotes_path)
    if quotes.is_empty():
        raise ValueError(f"Normalized quote parquet is empty: {quotes_path}")

    required = {"ts_client", "venue", "canonical_symbol", "market_status", "is_tradable"}
    missing = required.difference(quotes.columns)
    if missing:
        raise ValueError(f"Normalized quote parquet missing columns: {sorted(missing)}")

    cost_profiles = load_cost_profiles(cost_matrix_path)
    normalized_phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    normalized_execution_summary = normalize_execution_snapshot_summary(execution_summary)
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary
    )
    normalized_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        execution_diagnostics_summary
    )
    normalized_execution_gap_history_summary = normalize_execution_gap_history_summary(
        execution_gap_history_summary
    )
    normalized_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        execution_state_comparison_summary
    )
    normalized_execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
        execution_snapshot_drift_summary
    )
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    latest_execution_lineage = latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary=timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(timeline_latest_execution_comparison_summary),
        bundle_history_latest_execution_summary=(bundle_history_latest_execution_summary),
        bundle_history_latest_execution_comparison_summary=(
            bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=cycle_history_latest_execution_summary,
        cycle_history_latest_execution_comparison_summary=(
            cycle_history_latest_execution_comparison_summary
        ),
    )
    phase_gate_flat = phase_gate_flat_fields(normalized_phase_gate_summary)
    readiness_flat = readiness_flat_fields(normalized_readiness_summary)
    execution_flat = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        normalized_execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        normalized_execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        normalized_execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        normalized_execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    if signals_path is not None:
        signals = load_research_signals(signals_path)
        if signals:
            metrics, records, summary = _metrics_for_signals(
                quotes,
                signals,
                cost_profiles,
                exit_model=exit_model,
                holding_horizon_minutes=holding_horizon_minutes,
            )
            if isinstance(audit_summary, dict) and any(audit_summary.values()):
                summary["audit"] = audit_summary
            if normalized_phase_gate_summary and any(normalized_phase_gate_summary.values()):
                summary["phase_gate"] = normalized_phase_gate_summary
                summary.update(phase_gate_flat)
            if normalized_readiness_summary and any(normalized_readiness_summary.values()):
                summary["readiness_summary"] = normalized_readiness_summary
                summary.update(readiness_flat)
            if normalized_execution_summary and any(normalized_execution_summary.values()):
                summary["execution_summary"] = normalized_execution_summary
                summary.update(execution_flat)
            if normalized_execution_comparison_summary and any(
                normalized_execution_comparison_summary.values()
            ):
                summary["execution_comparison_summary"] = normalized_execution_comparison_summary
                summary.update(execution_comparison_flat)
            if normalized_execution_diagnostics_summary and any(
                normalized_execution_diagnostics_summary.values()
            ):
                summary["execution_diagnostics_summary"] = normalized_execution_diagnostics_summary
                summary.update(execution_diagnostics_flat)
            if normalized_execution_gap_history_summary and any(
                normalized_execution_gap_history_summary.values()
            ):
                summary["execution_gap_history_summary"] = normalized_execution_gap_history_summary
                summary.update(execution_gap_history_flat)
            if normalized_execution_state_comparison_summary and any(
                normalized_execution_state_comparison_summary.values()
            ):
                summary["execution_state_comparison_summary"] = (
                    normalized_execution_state_comparison_summary
                )
                summary.update(execution_state_comparison_flat)
            if normalized_execution_snapshot_drift_summary and any(
                normalized_execution_snapshot_drift_summary.values()
            ):
                summary["execution_snapshot_drift_summary"] = (
                    normalized_execution_snapshot_drift_summary
                )
                summary.update(execution_snapshot_drift_flat)
            if normalized_execution_drift_overview_summary and any(
                normalized_execution_drift_overview_summary.values()
            ):
                summary["execution_drift_overview_summary"] = (
                    normalized_execution_drift_overview_summary
                )
                summary.update(execution_drift_flat)
            summary.update(latest_execution_lineage)
            if decision_log_path is not None:
                _write_decision_records(records, decision_log_path)
            if decision_summary_path is not None:
                _write_decision_summary(summary, decision_summary_path)
            return metrics, records, summary

    metrics = [
        _metrics_for_group(group, cost_profiles)
        for (_key, group) in quotes.group_by(["venue", "canonical_symbol"], maintain_order=True)
    ]
    summary = {
        "mode": "quote_fallback",
        "exit_model": exit_model,
        "holding_horizon_minutes": holding_horizon_minutes,
        "signals_considered": 0,
        "executed_count": 0,
        "blocked_count": 0,
        "blocked_reason_counts": {},
        "records_written": 0,
    }
    if isinstance(audit_summary, dict) and any(audit_summary.values()):
        summary["audit"] = audit_summary
    if normalized_phase_gate_summary and any(normalized_phase_gate_summary.values()):
        summary["phase_gate"] = normalized_phase_gate_summary
        summary.update(phase_gate_flat)
    if normalized_readiness_summary and any(normalized_readiness_summary.values()):
        summary["readiness_summary"] = normalized_readiness_summary
        summary.update(readiness_flat)
    if normalized_execution_summary and any(normalized_execution_summary.values()):
        summary["execution_summary"] = normalized_execution_summary
        summary.update(execution_flat)
    if normalized_execution_comparison_summary and any(
        normalized_execution_comparison_summary.values()
    ):
        summary["execution_comparison_summary"] = normalized_execution_comparison_summary
        summary.update(execution_comparison_flat)
    if normalized_execution_diagnostics_summary and any(
        normalized_execution_diagnostics_summary.values()
    ):
        summary["execution_diagnostics_summary"] = normalized_execution_diagnostics_summary
        summary.update(execution_diagnostics_flat)
    if normalized_execution_gap_history_summary and any(
        normalized_execution_gap_history_summary.values()
    ):
        summary["execution_gap_history_summary"] = normalized_execution_gap_history_summary
        summary.update(execution_gap_history_flat)
    if normalized_execution_state_comparison_summary and any(
        normalized_execution_state_comparison_summary.values()
    ):
        summary["execution_state_comparison_summary"] = (
            normalized_execution_state_comparison_summary
        )
        summary.update(execution_state_comparison_flat)
    if normalized_execution_snapshot_drift_summary and any(
        normalized_execution_snapshot_drift_summary.values()
    ):
        summary["execution_snapshot_drift_summary"] = normalized_execution_snapshot_drift_summary
        summary.update(execution_snapshot_drift_flat)
    if normalized_execution_drift_overview_summary and any(
        normalized_execution_drift_overview_summary.values()
    ):
        summary["execution_drift_overview_summary"] = normalized_execution_drift_overview_summary
        summary.update(execution_drift_flat)
    summary.update(latest_execution_lineage)
    if decision_summary_path is not None:
        _write_decision_summary(summary, decision_summary_path)
    if decision_log_path is not None:
        _write_decision_records([], decision_log_path)
    return metrics, [], summary


def run_backtest_bridge_for_signals(
    quotes_path: Path,
    signals: list[ResearchSignal],
    cost_matrix_path: Path | None = None,
    exit_model: str = "next_row",
    holding_horizon_minutes: int | None = None,
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    if not quotes_path.exists():
        raise FileNotFoundError(f"Normalized quote parquet not found: {quotes_path}")
    quotes = pl.read_parquet(quotes_path)
    if quotes.is_empty():
        raise ValueError(f"Normalized quote parquet is empty: {quotes_path}")

    required = {"ts_client", "venue", "canonical_symbol", "market_status", "is_tradable"}
    missing = required.difference(quotes.columns)
    if missing:
        raise ValueError(f"Normalized quote parquet missing columns: {sorted(missing)}")

    return _metrics_for_signals(
        quotes,
        signals,
        load_cost_profiles(cost_matrix_path),
        exit_model=exit_model,
        holding_horizon_minutes=holding_horizon_minutes,
    )


def run_backtest_bridge(
    quotes_path: Path,
    signals_path: Path | None = None,
    cost_matrix_path: Path | None = None,
) -> list[BacktestMetrics]:
    metrics, _records, _summary = run_backtest_bridge_with_decisions(
        quotes_path,
        signals_path=signals_path,
        cost_matrix_path=cost_matrix_path,
    )
    return metrics


def write_backtest_report(
    metrics: list[BacktestMetrics],
    out_path: Path,
    signals_path: Path | None = None,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    readiness_summary = normalize_readiness_summary(readiness_summary)
    execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    source = (
        f"This report uses research signals from `{signals_path}` for virtual venue execution."
        if signals_path is not None and signals_path.exists()
        else "This report uses venue quote logs for virtual execution. It is not a trading signal generator."
    )
    rows = "\n".join(
        "| {venue} | {symbol} | {trades} | {total:.6f} | {drawdown:.6f} | {win_rate} | {cost:.2f} | {cost_source} | {stale} | {halt} |".format(
            venue=item.venue,
            symbol=item.canonical_symbol,
            trades=item.trade_count,
            total=item.total_return,
            drawdown=item.max_drawdown,
            win_rate="" if item.win_rate is None else f"{item.win_rate:.4f}",
            cost=item.cost_drag_bps,
            cost_source=item.cost_source or "",
            stale=item.stale_rejected_count,
            halt=item.halt_rejected_count,
        )
        for item in metrics
    )
    lines = [
        "# Backtest Bridge Report",
        "",
        source,
        "",
        "| Venue | Symbol | Trades | Total Return | Max Drawdown | Win Rate | Cost Drag bps | Cost Source | Stale Rejects | Halt Rejects |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
        rows,
        "",
    ]
    if isinstance(audit_summary, dict) and any(audit_summary.values()):
        audit_summary_flat = audit_summary_fields(audit_summary, audit_summary)
        lines.extend(
            [
                "## Audit Summary",
                "",
                f"- overall_status: {audit_summary_flat.get('overall_status') or ''}",
                f"- latest_operation: {audit_summary_flat.get('latest_operation') or ''}",
                f"- bundle_history_snapshot_count: {audit_summary_flat.get('bundle_history_snapshot_count') or ''}",
                "",
            ]
        )
    if isinstance(phase_gate_summary, dict) and any(phase_gate_summary.values()):
        phase_gate_flat = phase_gate_flat_fields(phase_gate_summary)
        lines.extend(
            [
                "## Phase Gate Summary",
                "",
                f"- decision: {phase_gate_flat.get('phase_gate_decision') or ''}",
                f"- phase2_entry_allowed: {phase_gate_flat.get('phase2_entry_allowed')}",
                f"- phase_gate_reason: {phase_gate_flat.get('phase_gate_reason') or ''}",
                f"- strict_validation_passed: {phase_gate_flat.get('strict_validation_passed')}",
                (
                    "- phase_gate_strict_validation_issue_count: "
                    f"{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}"
                ),
                f"- phase_gate_checked_files: {phase_gate_flat.get('phase_gate_checked_files')}",
                "",
            ]
        )
    if isinstance(readiness_summary, dict) and any(readiness_summary.values()):
        readiness_flat = readiness_flat_fields(readiness_summary)
        lines.extend(
            [
                "## Readiness Summary",
                "",
                f"- next_phase_candidate: {readiness_flat.get('readiness_next_phase_candidate') or ''}",
                f"- execution_ready: {readiness_flat.get('readiness_execution_ready')}",
                f"- phase_gate_decision: {readiness_flat.get('phase_gate_decision') or ''}",
                f"- phase2_entry_allowed: {readiness_flat.get('phase2_entry_allowed')}",
                "",
            ]
        )
    if isinstance(execution_summary, dict) and any(execution_summary.values()):
        execution_summary_flat = execution_snapshot_flat_fields(execution_summary)
        lines.extend(
            [
                "## Execution Snapshot",
                "",
                f"- overall_status: {execution_summary_flat.get('execution_overall_status') or ''}",
                f"- venue_count: {execution_summary_flat.get('execution_venue_count')}",
                f"- report_path: {execution_summary_flat.get('execution_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_comparison_summary, dict) and any(
        execution_comparison_summary.values()
    ):
        execution_comparison_flat = execution_comparison_flat_fields(execution_comparison_summary)
        lines.extend(
            [
                "## Execution Venue Comparison",
                "",
                (
                    "- all_registries_present: "
                    f"{execution_comparison_flat.get('execution_comparison_all_registries_present')}"
                ),
                f"- report_path: {execution_comparison_flat.get('execution_comparison_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_diagnostics_summary, dict) and any(
        execution_diagnostics_summary.values()
    ):
        execution_diagnostics_flat = execution_diagnostics_flat_fields(
            execution_diagnostics_summary
        )
        lines.extend(
            [
                "## Execution Venue Diagnostics",
                "",
                f"- overall_status: {execution_diagnostics_flat.get('execution_diagnostics_status') or ''}",
                f"- balance_gap_detected: {execution_diagnostics_flat.get('execution_balance_gap_detected')}",
                f"- fills_gap_detected: {execution_diagnostics_flat.get('execution_fills_gap_detected')}",
                f"- report_path: {execution_diagnostics_flat.get('execution_diagnostics_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_gap_history_summary, dict) and any(
        execution_gap_history_summary.values()
    ):
        execution_gap_history_flat = execution_gap_history_flat_fields(
            execution_gap_history_summary
        )
        lines.extend(
            [
                "## Execution Gap History",
                "",
                f"- entry_count: {execution_gap_history_flat.get('execution_gap_history_entry_count')}",
                f"- latest_status: {execution_gap_history_flat.get('execution_gap_history_latest_status') or ''}",
                (
                    "- latest_execution_diagnostics_status: "
                    f"{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status') or ''}"
                ),
                f"- report_path: {execution_gap_history_flat.get('execution_gap_history_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_state_comparison_summary, dict) and any(
        execution_state_comparison_summary.values()
    ):
        execution_state_comparison_flat = execution_state_comparison_flat_fields(
            execution_state_comparison_summary
        )
        lines.extend(
            [
                "## Execution State Comparison History",
                "",
                f"- entry_count: {execution_state_comparison_flat.get('execution_state_comparison_entry_count')}",
                (
                    "- latest_status_match: "
                    f"{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}"
                ),
                (
                    "- mismatching_count: "
                    f"{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}"
                ),
                f"- report_path: {execution_state_comparison_flat.get('execution_state_comparison_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_snapshot_drift_summary, dict) and any(
        execution_snapshot_drift_summary.values()
    ):
        execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
            execution_snapshot_drift_summary
        )
        lines.extend(
            [
                "## Execution Snapshot Drift History",
                "",
                f"- entry_count: {execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}",
                (
                    "- latest_status_match: "
                    f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}"
                ),
                (
                    "- mismatching_snapshot_count: "
                    f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}"
                ),
                f"- report_path: {execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_drift_overview_summary, dict) and any(
        execution_drift_overview_summary.values()
    ):
        execution_drift_flat = execution_drift_overview_flat_fields(
            execution_drift_overview_summary
        )
        lines.extend(
            [
                "## Execution Drift Overview",
                "",
                f"- overall_status: {execution_drift_flat.get('execution_drift_overview_status') or ''}",
                (
                    "- diagnostics_alignment_match: "
                    f"{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}"
                ),
                (
                    "- state_comparison_mismatching_count: "
                    f"{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}"
                ),
                (
                    "- snapshot_drift_mismatching_snapshot_count: "
                    f"{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
                ),
                f"- report_path: {execution_drift_flat.get('execution_drift_overview_report_path') or ''}",
                "",
            ]
        )
    lines.extend(
        latest_execution_sections(
            [
                (
                    "## Audit Timeline Latest Execution",
                    timeline_latest_execution_summary,
                    timeline_latest_execution_comparison_summary,
                ),
                (
                    "## Audit Bundle History Latest Execution",
                    bundle_history_latest_execution_summary,
                    bundle_history_latest_execution_comparison_summary,
                ),
                (
                    "## Cycle History Latest Execution",
                    cycle_history_latest_execution_summary,
                    cycle_history_latest_execution_comparison_summary,
                ),
            ]
        )
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_backtest_metrics_json(metrics: list[BacktestMetrics], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([asdict(item) for item in metrics], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_backtest_metrics_summary_json(
    metrics: list[BacktestMetrics],
    out_path: Path,
    *,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    trade_counts = [item.trade_count for item in metrics]
    avg_trade_returns = [
        item.avg_trade_return for item in metrics if item.avg_trade_return is not None
    ]
    normalized_phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    normalized_execution_summary = normalize_execution_snapshot_summary(execution_summary)
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary
    )
    normalized_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        execution_diagnostics_summary
    )
    normalized_execution_gap_history_summary = normalize_execution_gap_history_summary(
        execution_gap_history_summary
    )
    normalized_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        execution_state_comparison_summary
    )
    normalized_execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
        execution_snapshot_drift_summary
    )
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    latest_execution_lineage = latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary=timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(timeline_latest_execution_comparison_summary),
        bundle_history_latest_execution_summary=(bundle_history_latest_execution_summary),
        bundle_history_latest_execution_comparison_summary=(
            bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=cycle_history_latest_execution_summary,
        cycle_history_latest_execution_comparison_summary=(
            cycle_history_latest_execution_comparison_summary
        ),
    )
    phase_gate_flat = phase_gate_flat_fields(normalized_phase_gate_summary)
    readiness_flat = readiness_flat_fields(normalized_readiness_summary)
    execution_flat = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        normalized_execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        normalized_execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        normalized_execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        normalized_execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    payload = {
        "row_count": len(metrics),
        "venues": sorted({item.venue for item in metrics}),
        "symbols": sorted({item.canonical_symbol for item in metrics}),
        "total_trade_count": sum(trade_counts),
        "max_trade_count": max(trade_counts, default=0),
        "avg_trade_return_mean": (sum(avg_trade_returns) / len(avg_trade_returns))
        if avg_trade_returns
        else None,
        "max_drawdown_worst": min((item.max_drawdown for item in metrics), default=None),
        "cost_drag_bps_total": sum(item.cost_drag_bps for item in metrics),
        "stale_rejected_total": sum(item.stale_rejected_count for item in metrics),
        "halt_rejected_total": sum(item.halt_rejected_count for item in metrics),
        "audit": audit_summary if isinstance(audit_summary, dict) else {},
        "phase_gate": normalized_phase_gate_summary,
        **phase_gate_flat,
        "readiness_summary": normalized_readiness_summary,
        **readiness_flat,
        "execution": normalized_execution_summary,
        **execution_flat,
        "execution_comparison": normalized_execution_comparison_summary,
        **execution_comparison_flat,
        "execution_diagnostics": normalized_execution_diagnostics_summary,
        **execution_diagnostics_flat,
        "execution_gap_history_summary": normalized_execution_gap_history_summary,
        **execution_gap_history_flat,
        "execution_state_comparison_summary": normalized_execution_state_comparison_summary,
        **execution_state_comparison_flat,
        "execution_snapshot_drift_summary": normalized_execution_snapshot_drift_summary,
        **execution_snapshot_drift_flat,
        "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
        **execution_drift_flat,
        **latest_execution_lineage,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
