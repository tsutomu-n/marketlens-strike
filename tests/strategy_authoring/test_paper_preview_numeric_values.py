from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.paper_preview_numeric_values import (
    _float_or_default,
)


def test_float_or_default_converts_numeric_values() -> None:
    assert _float_or_default(1, 0.0) == 1.0
    assert _float_or_default(1.25, 0.0) == 1.25


def test_float_or_default_preserves_default_for_non_numeric_values() -> None:
    assert _float_or_default("1.25", 0.5) == 0.5
    assert _float_or_default(None, 0.5) == 0.5
    assert _float_or_default(object(), 0.5) == 0.5
