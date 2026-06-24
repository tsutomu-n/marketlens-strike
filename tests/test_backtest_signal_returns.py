from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sis.backtest.signal_returns import scaled_signal_return
from sis.backtest.signals import ResearchSignal


def _ts(hours: int) -> datetime:
    return datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc) + timedelta(hours=hours)


def _row(price: float | None) -> dict[str, object]:
    return {
        "exec_buy_price": price,
        "exec_sell_price": price - 0.1 if price is not None else None,
        "mark_price": price,
        "mid_price": price,
        "oracle_price": price,
        "index_price": price,
    }


def _signal(**overrides: object) -> ResearchSignal:
    values = {
        "ts_signal": _ts(0),
        "canonical_symbol": "XYZ100",
        "side": "long",
        "timeframe": "4h",
    }
    values.update(overrides)
    return ResearchSignal(**values)


def test_scaled_signal_return_closes_at_horizon_with_costs() -> None:
    signal_return, reason = scaled_signal_return(
        rows=[_row(100.0), _row(110.0)],
        quote_times=[_ts(0), _ts(4)],
        entry_index=0,
        horizon_exit_index=1,
        entry_price=100.0,
        side="long",
        cost_bps=5.0,
        signal=_signal(position_weight=0.5, max_fill_fraction=0.5),
        microstructure_fill_fraction=0.5,
    )

    assert signal_return == pytest.approx(((109.9 / 100.0 - 1.0) - 0.0005) * 0.5 * 0.25)
    assert reason == "fixed_horizon"


def test_scaled_signal_return_marks_missing_horizon_exit_price() -> None:
    assert scaled_signal_return(
        rows=[_row(100.0), _row(None)],
        quote_times=[_ts(0), _ts(4)],
        entry_index=0,
        horizon_exit_index=1,
        entry_price=100.0,
        side="long",
        cost_bps=0.0,
        signal=_signal(),
    ) == (0.0, "missing_exit_price")


def test_scaled_signal_return_includes_scale_event_reasons() -> None:
    signal_return, reason = scaled_signal_return(
        rows=[_row(100.0), _row(101.0), _row(102.0), _row(103.0), _row(110.0)],
        quote_times=[_ts(0), _ts(1), _ts(2), _ts(3), _ts(4)],
        entry_index=0,
        horizon_exit_index=4,
        entry_price=100.0,
        side="long",
        cost_bps=0.0,
        signal=_signal(),
        reduce_events=[(1, 0.25)],
        add_events=[(2, 0.5)],
        rebalance_events=[(3, 0.75, None)],
    )

    assert signal_return > 0
    assert reason == "add_signal+rebalance_signal+reduce_signal+fixed_horizon"


def test_scaled_signal_return_applies_bracket_time_stop() -> None:
    signal_return, reason = scaled_signal_return(
        rows=[_row(100.0), _row(101.0), _row(102.0)],
        quote_times=[_ts(0), _ts(1), _ts(2)],
        entry_index=0,
        horizon_exit_index=2,
        entry_price=100.0,
        side="long",
        cost_bps=0.0,
        signal=_signal(bracket_type="oco", bracket_time_stop_minutes=60),
    )

    assert signal_return == pytest.approx(100.9 / 100.0 - 1.0)
    assert reason == "bracket_time_stop"
