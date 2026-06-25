from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.position_entry_limits import (
    _position_entry_limit_block_reason,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import PositionRules


def _position(
    *,
    allow_opposing_open_positions: bool = False,
    allow_pyramiding: bool = False,
    max_open_signals_per_symbol: int | None = None,
    max_open_position_weight_per_symbol: float | None = None,
) -> PositionRules:
    return PositionRules(
        allow_opposing_open_positions=allow_opposing_open_positions,
        allow_pyramiding=allow_pyramiding,
        max_open_signals_per_symbol=max_open_signals_per_symbol,
        max_open_position_weight_per_symbol=max_open_position_weight_per_symbol,
    )


def _active(side: str, weight: float):
    return (datetime(2026, 1, 1, tzinfo=timezone.utc), side, weight)


def test_position_entry_limit_block_reason_prioritizes_opposing_position() -> None:
    reason = _position_entry_limit_block_reason(
        position=_position(
            allow_opposing_open_positions=False,
            allow_pyramiding=False,
            max_open_signals_per_symbol=1,
            max_open_position_weight_per_symbol=0.1,
        ),
        active=[_active("short", 0.4), _active("long", 0.4)],
        open_weight=0.8,
        side="long",
        weight=0.8,
    )

    assert reason == "position_opposing_open_position"


def test_position_entry_limit_block_reason_blocks_pyramiding_before_capacity() -> None:
    reason = _position_entry_limit_block_reason(
        position=_position(
            allow_opposing_open_positions=False,
            allow_pyramiding=False,
            max_open_signals_per_symbol=1,
            max_open_position_weight_per_symbol=0.1,
        ),
        active=[_active("long", 0.4)],
        open_weight=0.4,
        side="long",
        weight=0.2,
    )

    assert reason == "position_pyramiding_not_allowed"


def test_position_entry_limit_block_reason_blocks_open_signal_count() -> None:
    reason = _position_entry_limit_block_reason(
        position=_position(
            allow_opposing_open_positions=True,
            allow_pyramiding=True,
            max_open_signals_per_symbol=1,
        ),
        active=[_active("long", 0.4)],
        open_weight=0.4,
        side="long",
        weight=0.2,
    )

    assert reason == "position_open_signal_limit"


def test_position_entry_limit_block_reason_blocks_open_weight() -> None:
    reason = _position_entry_limit_block_reason(
        position=_position(
            allow_opposing_open_positions=True,
            allow_pyramiding=True,
            max_open_position_weight_per_symbol=0.5,
        ),
        active=[_active("long", 0.4)],
        open_weight=0.4,
        side="long",
        weight=0.2,
    )

    assert reason == "position_open_weight_limit"


def test_position_entry_limit_block_reason_returns_none_when_allowed() -> None:
    reason = _position_entry_limit_block_reason(
        position=_position(
            allow_opposing_open_positions=True,
            allow_pyramiding=True,
            max_open_signals_per_symbol=2,
            max_open_position_weight_per_symbol=1.0,
        ),
        active=[_active("long", 0.4)],
        open_weight=0.4,
        side="long",
        weight=0.2,
    )

    assert reason is None
