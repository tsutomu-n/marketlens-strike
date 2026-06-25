from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _exit_bps,
)
from sis.research.strategy_lab.authoring.compiler.trade_execution_quality_fields import (
    _trade_execution_quality_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_execution_risk_fields import (
    _trade_execution_risk_fields,
)


def _trade_execution_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "slippage_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "slippage_bps",
                _regime_value(regime, "slippage_bps", execution.slippage_bps),
            ),
            column=_override_column(
                execution_overrides,
                "slippage_bps",
                execution.slippage_bps_column,
            ),
        )
        or 0.0,
        **_trade_execution_quality_fields(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
        ),
        **_trade_execution_risk_fields(
            row=row,
            execution=execution,
            regime=regime,
            execution_overrides=execution_overrides,
        ),
    }
