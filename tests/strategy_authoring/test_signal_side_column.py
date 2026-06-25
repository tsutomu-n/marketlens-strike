from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.signal_side_column import _side_from_column
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


@pytest.mark.parametrize("value", ["buy", "bull", "long", " LONG "])
def test_side_from_column_maps_long_aliases(value: str) -> None:
    assert _side_from_column({"direction": value}, "direction") == "long"


@pytest.mark.parametrize("value", ["sell", "bear", "short", " SHORT "])
def test_side_from_column_maps_short_aliases(value: str) -> None:
    assert _side_from_column({"direction": value}, "direction") == "short"


@pytest.mark.parametrize("value", ["", None, "hold", "none", "skip", "flat"])
def test_side_from_column_maps_hold_aliases_to_none(value: object) -> None:
    assert _side_from_column({"direction": value}, "direction") == "none"


def test_side_from_column_rejects_unsupported_values_with_column_name() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="Unsupported side value in direction: sideways",
    ):
        _side_from_column({"direction": "sideways"}, "direction")
