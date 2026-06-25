from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl

from sis.research.strategy_lab.authoring.compiler.research_signal_adapter import (
    strategy_signals_to_research_signals,
)


def _row(*, ts_signal: datetime, signal_id: str, side: str, **overrides):
    base = {
        "ts_signal": ts_signal,
        "signal_id": signal_id,
        "execution_symbol": "xyz100",
        "side": side,
        "timeframe": "4H",
        "raw_score": 0.8,
        "stop_loss_bps": 150.0,
        "take_profit_bps": 300.0,
        "slippage_bps": None,
        "max_fill_fraction": None,
        "depth_participation_rate": None,
        "position_weight": None,
        "multi_leg_group_id": "",
        "multi_leg_leg_index": None,
        "multi_leg_leg_count": None,
        "multi_leg_anchor_real_market_symbol": "",
    }
    return base | overrides


def test_strategy_signals_to_research_signals_returns_empty_for_empty_frame() -> None:
    assert strategy_signals_to_research_signals(pl.DataFrame()) == []


def test_strategy_signals_to_research_signals_filters_sorts_and_applies_defaults() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frame = pl.DataFrame(
        [
            _row(ts_signal=start + timedelta(hours=1), signal_id="b", side="none"),
            _row(
                ts_signal=start + timedelta(hours=1),
                signal_id="c",
                side="long",
                execution_symbol="abc",
                multi_leg_group_id="group-1",
                multi_leg_leg_index=2,
                multi_leg_leg_count=2,
                multi_leg_anchor_real_market_symbol="AAA",
            ),
            _row(ts_signal=start, signal_id="a", side="short", execution_symbol="xyz"),
        ]
    )

    signals = strategy_signals_to_research_signals(frame)

    assert [signal.signal_id for signal in signals] == ["a", "c"]
    assert [signal.canonical_symbol for signal in signals] == ["XYZ", "ABC"]
    assert [signal.side for signal in signals] == ["short", "long"]
    assert signals[0].timeframe == "4h"
    assert signals[0].slippage_bps == 0.0
    assert signals[0].max_fill_fraction == 1.0
    assert signals[0].depth_participation_rate == 1.0
    assert signals[0].position_weight == 1.0
    assert signals[1].multi_leg_group_id == "group-1"
    assert signals[1].multi_leg_leg_index == 2
    assert signals[1].multi_leg_leg_count == 2
    assert signals[1].multi_leg_anchor_real_market_symbol == "AAA"
