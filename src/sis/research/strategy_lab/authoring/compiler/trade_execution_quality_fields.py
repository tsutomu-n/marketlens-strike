from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_numeric_values import _sizing_value
from sis.research.strategy_lab.authoring.compiler.trade_execution_latency_queue_fields import (
    _trade_execution_latency_queue_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_execution_liquidity_fields import (
    _trade_execution_liquidity_fields,
)


def _trade_execution_quality_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "max_fill_fraction": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_fill_fraction",
                _regime_value(regime, "max_fill_fraction", execution.max_fill_fraction),
            ),
            column=_override_column(
                execution_overrides,
                "max_fill_fraction",
                execution.max_fill_fraction_column,
            ),
        ),
        "min_fill_fraction": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_fill_fraction",
                _regime_value(regime, "min_fill_fraction", execution.min_fill_fraction),
            ),
            column=_override_column(
                execution_overrides,
                "min_fill_fraction",
                execution.min_fill_fraction_column,
            ),
        ),
        **_trade_execution_liquidity_fields(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
        ),
        **_trade_execution_latency_queue_fields(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
        ),
    }
