from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.portfolio_capacity.pack_reader import LoadedCandidatePack


def build_portfolio_capacity_inventory(loaded: LoadedCandidatePack) -> dict[str, Any]:
    windows_raw = loaded.rows.summary.get("execution_windows")
    if not isinstance(windows_raw, Mapping):
        raise ValueError("EXECUTION_WINDOWS_MISSING")
    intervals: list[tuple[datetime, datetime, str]] = []
    entry_times: Counter[datetime] = Counter()
    exit_times: Counter[datetime] = Counter()
    for event_id in loaded.rows.event_set:
        window = windows_raw.get(event_id)
        if not isinstance(window, Mapping):
            raise ValueError(f"EXECUTION_WINDOW_MISSING: {event_id}")
        raw_entry = window.get("entry_at")
        raw_exit = window.get("settled_at")
        if not isinstance(raw_entry, (datetime, str)) or not isinstance(raw_exit, (datetime, str)):
            raise ValueError(f"EXECUTION_WINDOW_TIMESTAMP_INVALID: {event_id}")
        entry = ensure_utc_aware("entry_at", raw_entry)
        exit_at = ensure_utc_aware("settled_at", raw_exit)
        intervals.append((entry, exit_at, event_id))
        entry_times[entry] += 1
        exit_times[exit_at] += 1
    same_timestamp_entry_exit_count = sum(
        min(entry_times[timestamp], exit_times[timestamp])
        for timestamp in set(entry_times).intersection(exit_times)
    )
    active_ends: list[datetime] = []
    peak_overlap = 0
    for entry, exit_at, _ in sorted(intervals):
        active_ends = [value for value in active_ends if value > entry]
        active_ends.append(exit_at)
        peak_overlap = max(peak_overlap, len(active_ends))

    action_counts = Counter(str(signal.get("selected_action") or "UNKNOWN") for signal in loaded.signals)
    symbol_counts = Counter(str(signal.get("symbol") or "").upper() for signal in loaded.signals)
    cost = cast(Mapping[str, Any], loaded.rows.summary["cost_assumptions"])
    operator_non_zero = sum(
        row.operator_time_cost_usd != Decimal("0")
        for row in loaded.rows.rows
        if row.action != "NO_TRADE"
    )
    backtest_summary = loaded.decision.summary.get("backtest")
    robustness = (
        backtest_summary.get("profit_robustness")
        if isinstance(backtest_summary, Mapping)
        else None
    )
    data_availability = loaded.decision.summary.get("data_availability")
    return {
        "schema_version": "crypto_perp_portfolio_capacity_inventory.v1",
        "pack_id": loaded.decision.pack_id,
        "row_set_id": loaded.rows.row_set_id,
        "event_count": len(loaded.rows.event_set),
        "unique_symbol_count": len([symbol for symbol in symbol_counts if symbol]),
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "selected_action_counts": dict(sorted(action_counts.items())),
        "time_range": {
            "entry_min": serialize_utc_z(min(entry for entry, _, _ in intervals)) if intervals else None,
            "exit_max": serialize_utc_z(max(exit_at for _, exit_at, _ in intervals)) if intervals else None,
        },
        "execution_window_peak_overlap": peak_overlap,
        "same_timestamp_entry_exit_count": same_timestamp_entry_exit_count,
        "notional_usd": str(cost.get("notional_usd")),
        "fee_rate": str(cost.get("fee_rate")),
        "funding_rate": str(cost.get("funding_rate")),
        "slippage_bps": str(cost.get("slippage_bps")),
        "operator_cost_non_zero_trade_row_count": operator_non_zero,
        "market_episode_count": (
            robustness.get("market_episode_count")
            if isinstance(robustness, Mapping)
            else None
        ),
        "data_availability_summary": dict(data_availability)
        if isinstance(data_availability, Mapping)
        else None,
        "known_gaps": list(loaded.rows.known_gaps),
        "actual_cash_used": False,
        "profit_proven": False,
    }
