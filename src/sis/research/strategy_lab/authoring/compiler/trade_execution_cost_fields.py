from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _exit_bps,
    _optional_float_from_row,
    _sizing_value,
)


def _trade_execution_cost_fields(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any = None,
    execution_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "min_borrow_availability_ratio": _sizing_value(
            row,
            fixed=_override_value(
                execution_overrides,
                "min_borrow_availability_ratio",
                _regime_value(
                    regime,
                    "min_borrow_availability_ratio",
                    execution.min_borrow_availability_ratio,
                ),
            ),
            column=_override_column(
                execution_overrides,
                "min_borrow_availability_ratio",
                execution.min_borrow_availability_ratio_column,
            ),
        ),
        "borrow_availability_ratio": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "borrow_availability_column",
                execution.borrow_availability_column,
            ),
        ),
        "max_borrow_cost_bps": _exit_bps(
            row,
            fixed=_override_value(
                execution_overrides,
                "max_borrow_cost_bps",
                _regime_value(regime, "max_borrow_cost_bps", execution.max_borrow_cost_bps),
            ),
            column=_override_column(
                execution_overrides,
                "max_borrow_cost_bps",
                execution.max_borrow_cost_bps_column,
            ),
        ),
        "borrow_cost_bps": _optional_float_from_row(
            row,
            _override_value(
                execution_overrides,
                "borrow_cost_column",
                execution.borrow_cost_column,
            ),
        ),
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
