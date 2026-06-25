from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.signal_weighted_score import (
    _weighted_score_value,
)
from sis.research.strategy_lab.authoring.contracts.core import ScoreTerm


def test_weighted_score_value_sums_numeric_terms() -> None:
    assert _weighted_score_value(
        {
            "research_return_1d": 0.03,
            "source_confidence": 0.8,
        },
        [
            ScoreTerm(column="research_return_1d", weight=10.0),
            ScoreTerm(column="source_confidence", weight=0.5),
        ],
    ) == pytest.approx(0.7)


def test_weighted_score_value_ignores_non_numeric_terms() -> None:
    assert _weighted_score_value(
        {
            "research_return_1d": "0.03",
            "source_confidence": 0.8,
        },
        [
            ScoreTerm(column="research_return_1d", weight=10.0),
            ScoreTerm(column="source_confidence", weight=0.5),
        ],
    ) == pytest.approx(0.4)


def test_weighted_score_value_returns_none_when_no_terms_are_usable() -> None:
    assert (
        _weighted_score_value(
            {"research_return_1d": "0.03"},
            [ScoreTerm(column="missing", weight=10.0)],
        )
        is None
    )
