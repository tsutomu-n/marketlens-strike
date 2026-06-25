from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.position_state_enabled import (
    _position_state_limits_enabled,
)


def _spec(*, position_enabled: bool = False, reduce_only: bool = False, reduce_only_column=None):
    return SimpleNamespace(
        rules=SimpleNamespace(
            position=SimpleNamespace(enabled=position_enabled),
            order=SimpleNamespace(
                reduce_only=reduce_only,
                reduce_only_column=reduce_only_column,
            ),
        )
    )


def test_position_state_limits_enabled_returns_false_without_position_or_reduce_only() -> None:
    assert _position_state_limits_enabled(_spec()) is False


def test_position_state_limits_enabled_returns_true_for_position_rules() -> None:
    assert _position_state_limits_enabled(_spec(position_enabled=True)) is True


def test_position_state_limits_enabled_returns_true_for_reduce_only_order_rules() -> None:
    assert _position_state_limits_enabled(_spec(reduce_only=True)) is True
    assert _position_state_limits_enabled(_spec(reduce_only_column="row_reduce_only")) is True
