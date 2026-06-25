from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.multi_leg_side import (
    _resolve_leg_side,
)


def test_resolve_leg_side_preserves_explicit_leg_side() -> None:
    assert _resolve_leg_side("long", "long") == "long"
    assert _resolve_leg_side("short", "long") == "long"
    assert _resolve_leg_side("long", "short") == "short"
    assert _resolve_leg_side("short", "short") == "short"


def test_resolve_leg_side_same_follows_base_side() -> None:
    assert _resolve_leg_side("long", "same") == "long"
    assert _resolve_leg_side("short", "same") == "short"


def test_resolve_leg_side_other_values_flip_base_side() -> None:
    assert _resolve_leg_side("long", "opposite") == "short"
    assert _resolve_leg_side("short", "opposite") == "long"
