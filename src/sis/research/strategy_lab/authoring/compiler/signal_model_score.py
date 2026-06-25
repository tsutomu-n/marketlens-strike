from __future__ import annotations

import math
from typing import Any

from sis.research.strategy_lab.authoring.contracts.core import ModelScore


def _model_score_value(row: dict[str, Any], model_score: ModelScore) -> float | None:
    total = model_score.intercept
    used = False
    for term in model_score.coefficients:
        value = row.get(term.column)
        if not isinstance(value, int | float) and model_score.missing_value is not None:
            value = model_score.missing_value
        if isinstance(value, int | float):
            total += float(value) * term.weight
            used = True
    if not used:
        return None
    if model_score.activation == "sigmoid":
        if total >= 0:
            z = math.exp(-total)
            return 1.0 / (1.0 + z)
        z = math.exp(total)
        return z / (1.0 + z)
    if model_score.activation == "tanh":
        return math.tanh(total)
    if model_score.activation == "clamp_0_1":
        return max(0.0, min(1.0, total))
    return total
