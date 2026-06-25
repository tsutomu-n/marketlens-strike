from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.order_row_values import (
    _entry_type_value as _entry_type_value,
    _optional_bool_from_row as _optional_bool_from_row,
    _time_in_force_value as _time_in_force_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def _optional_float_from_row(row: dict[str, Any], column: str | None) -> float | None:
    if column is None:
        return None
    value = row.get(column)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return None


def _exit_bps(row: dict[str, Any], *, fixed: float | None, column: str | None) -> float | None:
    dynamic = _optional_float_from_row(row, column)
    return dynamic if dynamic is not None else fixed


def _sizing_value(row: dict[str, Any], *, fixed: float | None, column: str | None) -> float | None:
    dynamic = _optional_float_from_row(row, column)
    return dynamic if dynamic is not None else fixed


def _non_negative_bps_value(
    row: dict[str, Any],
    *,
    fixed: float | None,
    column: str | None,
    field_name: str,
) -> float | None:
    value = _exit_bps(row, fixed=fixed, column=column)
    if value is not None and value < 0:
        raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
    return value


def _minutes_value(row: dict[str, Any], *, fixed: int | None, column: str | None) -> int | None:
    dynamic = _optional_float_from_row(row, column)
    if dynamic is None:
        return fixed
    if not float(dynamic).is_integer():
        raise StrategyAuthoringValidationError(f"{column} must be an integer minute value")
    return int(dynamic)


def _positive_integer_value(
    row: dict[str, Any],
    *,
    fixed: int | None,
    column: str | None,
    field_name: str,
) -> int | None:
    dynamic = _optional_float_from_row(row, column)
    value = fixed if dynamic is None else dynamic
    if value is None:
        return None
    if not float(value).is_integer():
        raise StrategyAuthoringValidationError(f"{field_name} must be an integer value")
    integer_value = int(value)
    if integer_value <= 0:
        raise StrategyAuthoringValidationError(f"{field_name} must be positive")
    return integer_value


def _non_negative_value(
    row: dict[str, Any],
    *,
    fixed: float | None,
    column: str | None,
    field_name: str,
) -> float | None:
    value = _sizing_value(row, fixed=fixed, column=column)
    if value is not None and value < 0:
        raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
    return value


def _unit_interval_value(
    row: dict[str, Any],
    *,
    fixed: float | None,
    column: str | None,
    field_name: str,
) -> float | None:
    value = _sizing_value(row, fixed=fixed, column=column)
    if value is not None and not 0.0 <= value <= 1.0:
        raise StrategyAuthoringValidationError(f"{field_name} must be between 0 and 1")
    return value
