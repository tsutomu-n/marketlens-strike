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


def _execution_pressure_limit_value(
    *,
    row: dict[str, Any],
    execution: Any,
    regime: Any,
    execution_overrides: dict[str, Any] | None,
    value_attr: str,
    column_attr: str,
) -> float | None:
    return _sizing_value(
        row,
        fixed=_override_value(
            execution_overrides,
            value_attr,
            _regime_value(regime, value_attr, getattr(execution, value_attr)),
        ),
        column=_override_column(
            execution_overrides,
            value_attr,
            getattr(execution, column_attr),
        ),
    )


def _execution_pressure_observed_value(
    *,
    row: dict[str, Any],
    execution: Any,
    execution_overrides: dict[str, Any] | None,
    override_column_key: str,
    column_attr: str,
) -> float | None:
    return _optional_float_from_row(
        row,
        _override_value(
            execution_overrides,
            override_column_key,
            getattr(execution, column_attr),
        ),
    )
