from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.trade_execution_cost_fields import (
    _trade_execution_cost_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_execution_pressure_fields import (
    _trade_execution_pressure_fields,
)


def _trade_execution_risk_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **_trade_execution_cost_fields(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
        ),
        **_trade_execution_pressure_fields(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
        ),
    }
