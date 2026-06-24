from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sis.backtest.fills import effective_fill_fraction
from sis.backtest.prices import execution_price, exit_price, gross_return_bps
from sis.backtest.signals import ResearchSignal


def scaled_signal_return(
    *,
    rows: Sequence[dict],
    quote_times: Sequence[datetime],
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

    def close_open_fraction(current_exit_price: float, fraction: float, reason: str) -> None:
        nonlocal open_legs
        to_close = max(fraction, 0.0)
        updated_legs: list[tuple[float, float]] = []
        for leg_entry_price, leg_fraction in open_legs:
            if to_close <= 0:
                updated_legs.append((leg_entry_price, leg_fraction))
                continue
            leg_close_fraction = min(leg_fraction, to_close)
            if leg_close_fraction > 0:
                exit_legs.append((leg_entry_price, current_exit_price, leg_close_fraction, reason))
                to_close -= leg_close_fraction
            remaining_leg_fraction = leg_fraction - leg_close_fraction
            if remaining_leg_fraction > 0:
                updated_legs.append((leg_entry_price, remaining_leg_fraction))
        open_legs = updated_legs

    def close_all(current_exit_price: float, reason: str) -> None:
        close_open_fraction(current_exit_price, open_fraction(), reason)

    for index in range(entry_index + 1, horizon_exit_index + 1):
        current_exit_price = exit_price(rows[index], side)
        if current_exit_price is None:
            continue
        exit_allowed = min_exit_index is None or index >= min_exit_index
        gross_bps = gross_return_bps(entry_price, current_exit_price, side)
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
                    close_open_fraction(current_exit_price, fraction, "reduce_signal")
            elif event_type == "add":
                add_entry_price = execution_price(rows[index], side)
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
                    close_open_fraction(
                        current_exit_price, current_open - target, "rebalance_signal"
                    )
                elif target > current_open:
                    rebalance_entry_price = execution_price(rows[index], side)
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
                    close_all(current_exit_price, "bracket_break_even_stop")
                    final_reason = "bracket_break_even_stop"
                    break
                if (
                    exit_rule == "stop_loss"
                    and signal.stop_loss_bps is not None
                    and gross_bps <= -signal.stop_loss_bps
                ):
                    final_reason = "bracket_stop_loss" if bracket_enabled else "stop_loss"
                    close_all(current_exit_price, final_reason)
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
                        close_open_fraction(current_exit_price, fraction, "partial_take_profit")
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
                    close_all(current_exit_price, final_reason)
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
                    close_all(current_exit_price, "trailing_stop")
                    final_reason = "trailing_stop"
                    break
                if (
                    exit_rule == "time_stop"
                    and time_stop_at is not None
                    and quote_times[index] >= time_stop_at
                ):
                    close_all(current_exit_price, "bracket_time_stop")
                    final_reason = "bracket_time_stop"
                    break
            if open_fraction() <= 0:
                break

    if open_fraction() > 0:
        horizon_price = exit_price(rows[horizon_exit_index], side)
        if horizon_price is None:
            return 0.0, "missing_exit_price"
        close_all(horizon_price, final_reason)

    gross_return = sum(
        (
            current_exit_price / leg_entry_price - 1.0
            if side != "short"
            else leg_entry_price / current_exit_price - 1.0
        )
        * fraction
        for leg_entry_price, current_exit_price, fraction, _reason in exit_legs
    )
    reason = "+".join(
        dict.fromkeys(
            [
                *marker_reasons,
                *(reason for _leg_entry_price, _exit_price, _fraction, reason in exit_legs),
            ]
        )
    )
    fill_fraction = effective_fill_fraction(signal, microstructure_fill_fraction)
    execution_cost_bps = cost_bps + signal.slippage_bps
    return (
        gross_return - execution_cost_bps / 10_000
    ) * signal.position_weight * fill_fraction, reason
