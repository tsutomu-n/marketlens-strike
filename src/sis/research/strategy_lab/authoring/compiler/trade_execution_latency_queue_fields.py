from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _optional_float_from_row,
    _sizing_value,
)


def _trade_execution_latency_queue_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "max_latency_ms": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_latency_ms",
                _regime_value(regime, "max_latency_ms", execution.max_latency_ms),
            ),
            column=_override_column(
                execution_overrides,
                "max_latency_ms",
                execution.max_latency_ms_column,
            ),
        ),
        "latency_ms": _optional_float_from_row(
            row,
            _override_value(execution_overrides, "latency_column", execution.latency_column),
        ),
        "min_queue_position_score": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_queue_position_score",
                _regime_value(
                    regime,
                    "min_queue_position_score",
                    execution.min_queue_position_score,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "min_queue_position_score",
                execution.min_queue_position_score_column,
            ),
        ),
        "queue_position_score": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "queue_position_score_column",
                execution.queue_position_score_column,
            ),
        ),
    }
