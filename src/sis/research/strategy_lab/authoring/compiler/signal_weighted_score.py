from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sis.research.strategy_lab.authoring.contracts.core import ScoreTerm


def _weighted_score_value(row: dict[str, Any], terms: Sequence[ScoreTerm]) -> float | None:
    total = 0.0
    used = False
    for term in terms:
        value = row.get(term.column)
        if isinstance(value, int | float):
            total += float(value) * term.weight
            used = True
    return total if used else None
