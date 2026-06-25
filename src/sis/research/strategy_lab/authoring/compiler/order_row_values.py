from __future__ import annotations

from typing import Any, Literal, cast

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def _entry_type_value(
    row: dict[str, Any],
    *,
    fixed: Literal["market", "limit", "stop_market"],
    column: str | None,
) -> Literal["market", "limit", "stop_market"]:
    if column is None:
        return fixed
    value = row.get(column)
    if value is None or (isinstance(value, str) and not value.strip()):
        return fixed
    normalized = str(value).strip().lower()
    if normalized in {"market", "limit", "stop_market"}:
        return cast(Literal["market", "limit", "stop_market"], normalized)
    raise StrategyAuthoringValidationError(
        f"Unsupported rules.order.entry_type_column value: {value}"
    )


def _time_in_force_value(
    row: dict[str, Any],
    *,
    fixed: Literal["gtc", "gtd", "ioc", "fok"],
    column: str | None,
) -> Literal["gtc", "gtd", "ioc", "fok"]:
    if column is None:
        return fixed
    value = row.get(column)
    if value is None or (isinstance(value, str) and not value.strip()):
        return fixed
    normalized = str(value).strip().lower()
    if normalized in {"gtc", "gtd", "ioc", "fok"}:
        return cast(Literal["gtc", "gtd", "ioc", "fok"], normalized)
    raise StrategyAuthoringValidationError(
        f"Unsupported rules.order.time_in_force_column value: {value}"
    )


def _optional_bool_from_row(row: dict[str, Any], column: str | None) -> bool | None:
    if column is None:
        return None
    value = row.get(column)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise StrategyAuthoringValidationError(f"Unsupported boolean value in {column}: {value}")
