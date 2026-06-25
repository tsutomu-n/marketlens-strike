from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_numeric_values import (
    _exit_bps,
    _optional_float_from_row,
)


def _trade_execution_tax_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "max_tax_drag_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_tax_drag_bps",
                _regime_value(regime, "max_tax_drag_bps", execution.max_tax_drag_bps),
            ),
            column=_override_column(
                execution_overrides,
                "max_tax_drag_bps",
                execution.max_tax_drag_bps_column,
            ),
        ),
        "tax_drag_bps": _optional_float_from_row(
            row,
            _override_value(execution_overrides, "tax_drag_column", execution.tax_drag_column),
        ),
    }
