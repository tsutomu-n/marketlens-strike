from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature

ARITHMETIC_DERIVED_OPS = {
    "add",
    "sub",
    "mul",
    "div",
    "ratio",
    "diff",
    "pct_diff",
    "abs",
    "neg",
    "max",
    "min",
    "mean",
}


def literal_or_col(feature: DerivedFeature, index: int = 1) -> pl.Expr:
    if len(feature.columns) > index:
        return pl.col(feature.columns[index])
    if feature.value is None:
        raise StrategyAuthoringValidationError(
            f"derived feature {feature.name} requires column {index + 1} or value"
        )
    return pl.lit(feature.value)


def safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def arithmetic_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])

    if feature.op == "add":
        expr = first
        for column in feature.columns[1:]:
            expr = expr + pl.col(column)
        if feature.value is not None:
            expr = expr + feature.value
        return expr
    if feature.op == "sub":
        return first - literal_or_col(feature)
    if feature.op == "mul":
        expr = first
        for column in feature.columns[1:]:
            expr = expr * pl.col(column)
        if feature.value is not None:
            expr = expr * feature.value
        return expr
    if feature.op in {"div", "ratio"}:
        denominator = literal_or_col(feature)
        return first / safe_denominator(denominator)
    if feature.op == "diff":
        return first - literal_or_col(feature)
    if feature.op == "pct_diff":
        denominator = literal_or_col(feature)
        return (first - denominator) / safe_denominator(denominator)
    if feature.op == "abs":
        return first.abs()
    if feature.op == "neg":
        return -first
    if feature.op == "max":
        expr = pl.max_horizontal([pl.col(column) for column in feature.columns])
        if feature.value is not None:
            expr = pl.max_horizontal([expr, pl.lit(feature.value)])
        return expr
    if feature.op == "min":
        expr = pl.min_horizontal([pl.col(column) for column in feature.columns])
        if feature.value is not None:
            expr = pl.min_horizontal([expr, pl.lit(feature.value)])
        return expr
    expressions = [pl.col(column) for column in feature.columns]
    if feature.value is not None:
        expressions.append(pl.lit(feature.value))
    return pl.mean_horizontal(expressions)
