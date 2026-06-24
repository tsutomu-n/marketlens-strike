from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.backtest.exits import resolve_signal_exit
from sis.backtest.signals import ResearchSignal


def _ts(minutes: int) -> datetime:
    return datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)


def _signal(side: str = "long", minutes: int = 0, **overrides: object) -> ResearchSignal:
    values = {
        "ts_signal": _ts(minutes),
        "canonical_symbol": "XYZ100",
        "side": side,
        "timeframe": "4h",
    }
    values.update(overrides)
    return ResearchSignal(**values)


def test_resolve_signal_exit_uses_fixed_horizon_first_quote_after_target() -> None:
    result = resolve_signal_exit(
        signal=_signal(),
        symbol_signals=[_signal()],
        quote_times=[_ts(0), _ts(60), _ts(240)],
        entry_index=0,
        exit_model="fixed_horizon",
        holding_horizon_minutes=240,
    )

    assert result is not None
    assert result.exit_index == 2
    assert result.final_exit_reason == "fixed_horizon"
    assert result.min_exit_index is None


def test_resolve_signal_exit_returns_none_when_required_exit_is_missing() -> None:
    assert (
        resolve_signal_exit(
            signal=_signal(),
            symbol_signals=[_signal()],
            quote_times=[_ts(0), _ts(60)],
            entry_index=0,
            exit_model="fixed_horizon",
            holding_horizon_minutes=240,
        )
        is None
    )
    assert (
        resolve_signal_exit(
            signal=_signal(min_holding_minutes=120),
            symbol_signals=[_signal(min_holding_minutes=120)],
            quote_times=[_ts(0), _ts(60)],
            entry_index=0,
            exit_model="next_row",
            holding_horizon_minutes=None,
        )
        is None
    )


def test_resolve_signal_exit_applies_min_and_max_holding_boundaries() -> None:
    min_result = resolve_signal_exit(
        signal=_signal(min_holding_minutes=120),
        symbol_signals=[_signal(min_holding_minutes=120)],
        quote_times=[_ts(0), _ts(60), _ts(120), _ts(240)],
        entry_index=0,
        exit_model="next_row",
        holding_horizon_minutes=None,
    )
    max_result = resolve_signal_exit(
        signal=_signal(max_holding_minutes=60),
        symbol_signals=[_signal(max_holding_minutes=60)],
        quote_times=[_ts(0), _ts(60), _ts(120), _ts(240)],
        entry_index=0,
        exit_model="fixed_horizon",
        holding_horizon_minutes=240,
    )

    assert min_result is not None
    assert min_result.exit_index == 2
    assert min_result.min_exit_index == 2
    assert min_result.final_exit_reason == "next_row"
    assert max_result is not None
    assert max_result.exit_index == 1
    assert max_result.final_exit_reason == "max_holding_time"


def test_resolve_signal_exit_supports_close_and_opposite_marker_exits() -> None:
    close_result = resolve_signal_exit(
        signal=_signal(exit_on_close_signal=True),
        symbol_signals=[_signal(exit_on_close_signal=True), _signal("close", 60)],
        quote_times=[_ts(0), _ts(60), _ts(240)],
        entry_index=0,
        exit_model="fixed_horizon",
        holding_horizon_minutes=240,
    )
    opposite_result = resolve_signal_exit(
        signal=_signal(exit_on_opposite_signal=True),
        symbol_signals=[_signal(exit_on_opposite_signal=True), _signal("short", 60)],
        quote_times=[_ts(0), _ts(60), _ts(240)],
        entry_index=0,
        exit_model="fixed_horizon",
        holding_horizon_minutes=240,
    )

    assert close_result is not None
    assert close_result.exit_index == 1
    assert close_result.final_exit_reason == "close_signal"
    assert opposite_result is not None
    assert opposite_result.exit_index == 1
    assert opposite_result.final_exit_reason == "opposite_signal"


def test_resolve_signal_exit_collects_scale_events_before_final_exit() -> None:
    result = resolve_signal_exit(
        signal=_signal(
            exit_on_reduce_signal=True,
            exit_on_add_signal=True,
            exit_on_rebalance_signal=True,
        ),
        symbol_signals=[
            _signal(
                exit_on_reduce_signal=True,
                exit_on_add_signal=True,
                exit_on_rebalance_signal=True,
            ),
            _signal("reduce", 60, reduce_fraction=0.25),
            _signal("add", 120, add_fraction=0.5),
            _signal(
                "rebalance",
                180,
                rebalance_target_fraction=0.75,
                rebalance_min_delta_fraction=0.1,
            ),
        ],
        quote_times=[_ts(0), _ts(60), _ts(120), _ts(180), _ts(240)],
        entry_index=0,
        exit_model="fixed_horizon",
        holding_horizon_minutes=240,
    )

    assert result is not None
    assert result.exit_index == 4
    assert result.reduce_events == [(1, 0.25)]
    assert result.add_events == [(2, 0.5)]
    assert result.rebalance_events == [(3, 0.75, 0.1)]
