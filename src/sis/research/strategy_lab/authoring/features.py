from __future__ import annotations

from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
    _stable_digest,
)
from sis.research.strategy_lab.authoring.contracts.core import Condition
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.derived_features import (
    apply_derived_features as _apply_derived_features,
)
from sis.research.strategy_lab.authoring.required_columns import _all_conditions

__all__ = ["_apply_derived_features"]

ADVANCED_CONDITION_OPERATORS = {
    "crosses_above",
    "crosses_below",
    "rising",
    "falling",
    "consecutive_gt",
    "consecutive_gte",
    "consecutive_lt",
    "consecutive_lte",
    "consecutive_eq",
    "consecutive_neq",
}


def _condition_feature_name(condition: Condition) -> str:
    payload = condition.model_dump(mode="json", exclude_none=True)
    return f"__condition_{_stable_digest(payload)}"


def _condition_target_expr(condition: Condition) -> pl.Expr:
    return (
        pl.col(condition.value_column)
        if condition.value_column is not None
        else pl.lit(condition.value)
    )


def _condition_comparison_expr(condition: Condition) -> pl.Expr:
    target = _condition_target_expr(condition)
    value = pl.col(condition.column)
    op = condition.op.removeprefix("consecutive_")
    if op == "gt":
        return value > target
    if op == "gte":
        return value >= target
    if op == "lt":
        return value < target
    if op == "lte":
        return value <= target
    if op == "eq":
        return value == target
    if op == "neq":
        return value != target
    raise StrategyAuthoringValidationError(f"Unsupported advanced comparison: {condition.op}")


def _condition_feature_expr(condition: Condition) -> pl.Expr:
    value = pl.col(condition.column)
    if condition.op in {"crosses_above", "crosses_below"}:
        target = _condition_target_expr(condition)
        previous_value = value.shift(1).over("canonical_symbol")
        previous_target = (
            pl.col(condition.value_column).shift(1).over("canonical_symbol")
            if condition.value_column is not None
            else pl.lit(condition.value)
        )
        if condition.op == "crosses_above":
            expr = (value > target) & (previous_value <= previous_target)
        else:
            expr = (value < target) & (previous_value >= previous_target)
    elif condition.op in {"rising", "falling"}:
        previous_value = value.shift(condition.window or 1).over("canonical_symbol")
        expr = value > previous_value if condition.op == "rising" else value < previous_value
    elif condition.op.startswith("consecutive_"):
        base = _condition_comparison_expr(condition).cast(pl.Int8)
        expr = (
            base.rolling_min(window_size=condition.window or 1, min_samples=condition.window or 1)
            .over("canonical_symbol")
            .fill_null(0)
            == 1
        )
    else:
        raise StrategyAuthoringValidationError(f"Unsupported advanced condition: {condition.op}")
    return expr.fill_null(False).alias(_condition_feature_name(condition))


def _apply_condition_features(frame: pl.DataFrame, spec: StrategyAuthoringSpec) -> pl.DataFrame:
    conditions = [
        condition
        for condition in _all_conditions(spec)
        if condition.op in ADVANCED_CONDITION_OPERATORS
    ]
    if not conditions:
        return frame
    enriched = frame.sort(["canonical_symbol", "ts"])
    seen: set[str] = set()
    for condition in conditions:
        name = _condition_feature_name(condition)
        if name in seen:
            continue
        seen.add(name)
        enriched = enriched.with_columns(_condition_feature_expr(condition))
    return enriched


def _condition_passes(row: dict[str, Any], condition: Condition) -> bool:
    if condition.op in ADVANCED_CONDITION_OPERATORS:
        return bool(row.get(_condition_feature_name(condition)))
    value = row.get(condition.column)
    if condition.op == "is_true":
        return value is True
    if condition.op == "is_false":
        return value is False
    if value is None:
        return False
    target = (
        row.get(condition.value_column) if condition.value_column is not None else condition.value
    )
    if target is None:
        return False
    if condition.op == "gt":
        return value > target
    if condition.op == "gte":
        return value >= target
    if condition.op == "lt":
        return value < target
    if condition.op == "lte":
        return value <= target
    if condition.op == "eq":
        return value == target
    if condition.op == "neq":
        return value != target
    if condition.op == "between":
        low, high = target
        return low <= value <= high
    if condition.op == "in":
        return value in target
    if condition.op == "not_in":
        return value not in target
    raise StrategyAuthoringValidationError(f"Unsupported operator: {condition.op}")
