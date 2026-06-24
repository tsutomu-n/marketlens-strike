from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.backtest.fills import (
    effective_fill_fraction,
    entry_fill_index,
    microstructure_fill_fraction,
)
from sis.backtest.signals import ResearchSignal


def _signal(**overrides: object) -> ResearchSignal:
    values = {
        "ts_signal": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
        "canonical_symbol": "XYZ100",
        "side": "long",
        "timeframe": "4h",
    }
    values.update(overrides)
    return ResearchSignal(**values)


def _row(price: float, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "exec_buy_price": price,
        "exec_sell_price": price - 0.1,
        "mark_price": price,
        "mid_price": price,
        "oracle_price": price,
        "index_price": price,
        "spread_bps": 1.0,
    }
    row.update(overrides)
    return row


def test_market_entry_fills_at_reference_index() -> None:
    rows = [_row(100.0), _row(99.0)]
    quote_times = [
        datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 22, 0, 1, tzinfo=timezone.utc),
    ]

    assert entry_fill_index(
        rows=rows,
        quote_times=quote_times,
        reference_index=0,
        signal=_signal(entry_order_type="market"),
    ) == (0, None)


def test_limit_and_stop_market_entries_wait_for_trigger_price() -> None:
    quote_times = [
        datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 22, 0, 1, tzinfo=timezone.utc),
    ]

    assert entry_fill_index(
        rows=[_row(100.0), _row(98.9)],
        quote_times=quote_times,
        reference_index=0,
        signal=_signal(entry_order_type="limit", entry_limit_offset_bps=100.0),
    ) == (1, None)
    assert entry_fill_index(
        rows=[_row(100.0), _row(101.1)],
        quote_times=quote_times,
        reference_index=0,
        signal=_signal(entry_order_type="stop_market", entry_stop_offset_bps=100.0),
    ) == (1, None)


def test_ioc_fok_timeout_and_post_only_blocks_return_existing_reason_strings() -> None:
    start = datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc)

    assert entry_fill_index(
        rows=[_row(100.0), _row(98.9)],
        quote_times=[start, start + timedelta(minutes=1)],
        reference_index=0,
        signal=_signal(
            entry_order_type="limit",
            entry_limit_offset_bps=100.0,
            entry_time_in_force="ioc",
        ),
    ) == (None, "entry_order_unfilled")
    assert entry_fill_index(
        rows=[_row(100.0), _row(98.9)],
        quote_times=[start, start + timedelta(minutes=1)],
        reference_index=0,
        signal=_signal(
            entry_order_type="limit",
            entry_limit_offset_bps=100.0,
            entry_time_in_force="fok",
        ),
    ) == (None, "entry_order_unfilled")
    assert entry_fill_index(
        rows=[_row(100.0), _row(98.9)],
        quote_times=[start, start + timedelta(minutes=31)],
        reference_index=0,
        signal=_signal(
            entry_order_type="limit",
            entry_limit_offset_bps=100.0,
            entry_timeout_minutes=30,
        ),
    ) == (None, "entry_order_unfilled")
    assert entry_fill_index(
        rows=[_row(100.0), _row(99.0)],
        quote_times=[start, start + timedelta(minutes=1)],
        reference_index=0,
        signal=_signal(
            entry_order_type="limit",
            entry_limit_offset_bps=0.0,
            entry_post_only=True,
        ),
    ) == (None, "entry_order_post_only_would_cross")


def test_effective_and_microstructure_fill_fraction() -> None:
    assert effective_fill_fraction(_signal(max_fill_fraction=0.5), 0.25) == 0.125
    assert microstructure_fill_fraction(
        _signal(min_depth_usd=1_000.0, notional_usd=500.0, depth_participation_rate=0.5),
        _row(100.0, min_side_depth_10bps_usd=1_000.0),
    ) == (1.0, None)
    assert microstructure_fill_fraction(
        _signal(min_depth_usd=1_000.0, notional_usd=2_000.0, depth_participation_rate=0.5),
        _row(100.0, min_side_depth_10bps_usd=1_000.0),
    ) == (0.25, None)
    assert microstructure_fill_fraction(
        _signal(max_spread_bps=2.0),
        _row(100.0, spread_bps=3.0),
    ) == (None, "microstructure_spread_too_wide")
