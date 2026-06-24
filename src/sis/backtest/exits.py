from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sis.backtest.signals import ResearchSignal


@dataclass(frozen=True)
class ExitResolution:
    exit_index: int
    final_exit_reason: str
    min_exit_index: int | None
    reduce_events: list[tuple[int, float]]
    add_events: list[tuple[int, float]]
    rebalance_events: list[tuple[int, float, float | None]]


def resolve_signal_exit(
    *,
    signal: ResearchSignal,
    symbol_signals: Sequence[ResearchSignal],
    quote_times: Sequence[datetime],
    entry_index: int,
    exit_model: str,
    holding_horizon_minutes: int | None,
) -> ExitResolution | None:
    if exit_model == "fixed_horizon":
        target_exit_ts = quote_times[entry_index] + timedelta(minutes=holding_horizon_minutes or 0)
        exit_index = _first_quote_index_at_or_after(
            quote_times=quote_times,
            start_index=entry_index + 1,
            target_ts=target_exit_ts,
        )
    else:
        exit_index = entry_index + 1 if entry_index + 1 < len(quote_times) else None
    final_exit_reason = "fixed_horizon" if exit_model == "fixed_horizon" else "next_row"
    if exit_index is None:
        return None

    min_exit_index = _min_exit_index(signal, quote_times, entry_index)
    if signal.min_holding_minutes is not None and min_exit_index is None:
        return None
    if min_exit_index is not None:
        exit_index = max(exit_index, min_exit_index)

    if signal.max_holding_minutes is not None:
        max_exit_ts = quote_times[entry_index] + timedelta(minutes=signal.max_holding_minutes)
        max_exit_index = _first_quote_index_at_or_after(
            quote_times=quote_times,
            start_index=entry_index + 1,
            target_ts=max_exit_ts,
        )
        if max_exit_index is None:
            return None
        if min_exit_index is not None and max_exit_index < min_exit_index:
            max_exit_index = min_exit_index
        if max_exit_index < exit_index:
            exit_index = max_exit_index
            final_exit_reason = "max_holding_time"

    min_marker_ts = (
        quote_times[entry_index] + timedelta(minutes=signal.min_holding_minutes)
        if signal.min_holding_minutes is not None
        else None
    )
    if signal.exit_on_close_signal:
        close_index = _first_marker_exit_index(
            signal=signal,
            symbol_signals=symbol_signals,
            quote_times=quote_times,
            entry_index=entry_index,
            exit_index=exit_index,
            min_marker_ts=min_marker_ts,
            marker_sides={"close"},
        )
        if close_index is not None:
            exit_index = close_index
            final_exit_reason = "close_signal"

    reduce_events = (
        _marker_events(
            signal=signal,
            symbol_signals=symbol_signals,
            quote_times=quote_times,
            entry_index=entry_index,
            exit_index=exit_index,
            min_marker_ts=min_marker_ts,
            marker_side="reduce",
            value_getter=lambda item: item.reduce_fraction or 1.0,
        )
        if signal.exit_on_reduce_signal
        else []
    )
    add_events = (
        _marker_events(
            signal=signal,
            symbol_signals=symbol_signals,
            quote_times=quote_times,
            entry_index=entry_index,
            exit_index=exit_index,
            min_marker_ts=min_marker_ts,
            marker_side="add",
            value_getter=lambda item: item.add_fraction or 1.0,
        )
        if signal.exit_on_add_signal
        else []
    )
    rebalance_events = (
        _rebalance_events(
            signal=signal,
            symbol_signals=symbol_signals,
            quote_times=quote_times,
            entry_index=entry_index,
            exit_index=exit_index,
            min_marker_ts=min_marker_ts,
        )
        if signal.exit_on_rebalance_signal
        else []
    )

    if signal.exit_on_opposite_signal:
        opposite_index = _first_marker_exit_index(
            signal=signal,
            symbol_signals=symbol_signals,
            quote_times=quote_times,
            entry_index=entry_index,
            exit_index=exit_index,
            min_marker_ts=min_marker_ts,
            marker_sides={"long", "short"} - {signal.side},
        )
        if opposite_index is not None:
            exit_index = opposite_index
            final_exit_reason = "opposite_signal"

    return ExitResolution(
        exit_index=exit_index,
        final_exit_reason=final_exit_reason,
        min_exit_index=min_exit_index,
        reduce_events=reduce_events,
        add_events=add_events,
        rebalance_events=rebalance_events,
    )


def _min_exit_index(
    signal: ResearchSignal, quote_times: Sequence[datetime], entry_index: int
) -> int | None:
    if signal.min_holding_minutes is None:
        return None
    min_exit_ts = quote_times[entry_index] + timedelta(minutes=signal.min_holding_minutes)
    return _first_quote_index_at_or_after(
        quote_times=quote_times,
        start_index=entry_index + 1,
        target_ts=min_exit_ts,
    )


def _first_quote_index_at_or_after(
    *, quote_times: Sequence[datetime], start_index: int, target_ts: datetime
) -> int | None:
    return next(
        (
            index
            for index, quote_time in enumerate(quote_times[start_index:], start=start_index)
            if quote_time >= target_ts
        ),
        None,
    )


def _marker_is_eligible(
    *,
    entry_signal: ResearchSignal,
    marker_signal: ResearchSignal,
    min_marker_ts: datetime | None,
    marker_sides: set[str],
) -> bool:
    return (
        marker_signal.ts_signal > entry_signal.ts_signal
        and marker_signal.side in marker_sides
        and (min_marker_ts is None or marker_signal.ts_signal >= min_marker_ts)
    )


def _first_marker_exit_index(
    *,
    signal: ResearchSignal,
    symbol_signals: Sequence[ResearchSignal],
    quote_times: Sequence[datetime],
    entry_index: int,
    exit_index: int,
    min_marker_ts: datetime | None,
    marker_sides: set[str],
) -> int | None:
    marker_signal = next(
        (
            item
            for item in symbol_signals
            if _marker_is_eligible(
                entry_signal=signal,
                marker_signal=item,
                min_marker_ts=min_marker_ts,
                marker_sides=marker_sides,
            )
        ),
        None,
    )
    if marker_signal is None:
        return None
    marker_index = _first_quote_index_at_or_after(
        quote_times=quote_times,
        start_index=entry_index + 1,
        target_ts=marker_signal.ts_signal,
    )
    if marker_index is not None and marker_index < exit_index:
        return marker_index
    return None


def _marker_events(
    *,
    signal: ResearchSignal,
    symbol_signals: Sequence[ResearchSignal],
    quote_times: Sequence[datetime],
    entry_index: int,
    exit_index: int,
    min_marker_ts: datetime | None,
    marker_side: str,
    value_getter,
) -> list[tuple[int, float]]:
    events: list[tuple[int, float]] = []
    for marker_signal in (
        item
        for item in symbol_signals
        if _marker_is_eligible(
            entry_signal=signal,
            marker_signal=item,
            min_marker_ts=min_marker_ts,
            marker_sides={marker_side},
        )
    ):
        marker_index = _first_quote_index_at_or_after(
            quote_times=quote_times,
            start_index=entry_index + 1,
            target_ts=marker_signal.ts_signal,
        )
        if marker_index is not None and marker_index < exit_index:
            events.append((marker_index, value_getter(marker_signal)))
    return events


def _rebalance_events(
    *,
    signal: ResearchSignal,
    symbol_signals: Sequence[ResearchSignal],
    quote_times: Sequence[datetime],
    entry_index: int,
    exit_index: int,
    min_marker_ts: datetime | None,
) -> list[tuple[int, float, float | None]]:
    events: list[tuple[int, float, float | None]] = []
    for marker_signal in (
        item
        for item in symbol_signals
        if _marker_is_eligible(
            entry_signal=signal,
            marker_signal=item,
            min_marker_ts=min_marker_ts,
            marker_sides={"rebalance"},
        )
    ):
        marker_index = _first_quote_index_at_or_after(
            quote_times=quote_times,
            start_index=entry_index + 1,
            target_ts=marker_signal.ts_signal,
        )
        if marker_index is not None and marker_index < exit_index:
            events.append(
                (
                    marker_index,
                    marker_signal.rebalance_target_fraction or 0.0,
                    marker_signal.rebalance_min_delta_fraction,
                )
            )
    return events
