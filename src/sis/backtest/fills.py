from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta

from sis.backtest.prices import execution_price
from sis.backtest.signals import ResearchSignal


QuoteRow = Mapping[str, object]


def entry_fill_index(
    *,
    rows: Sequence[QuoteRow],
    quote_times: Sequence[datetime],
    reference_index: int,
    signal: ResearchSignal,
) -> tuple[int | None, str | None]:
    order_type = signal.entry_order_type
    if order_type == "market":
        return reference_index, None
    reference_price = execution_price(rows[reference_index], signal.side)
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
        price = execution_price(rows[index], signal.side)
        if price is not None and (
            price >= trigger_price if comparison == "gte" else price <= trigger_price
        ):
            if signal.entry_post_only and index == reference_index:
                return None, "entry_order_post_only_would_cross"
            return index, None
    return None, "entry_order_unfilled"


def effective_fill_fraction(signal: ResearchSignal, microstructure_fill_fraction: float) -> float:
    return min(max(signal.max_fill_fraction, 0.0), 1.0) * min(
        max(microstructure_fill_fraction, 0.0), 1.0
    )


def microstructure_fill_fraction(
    signal: ResearchSignal, entry: QuoteRow
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
