from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


CROSS_SECTIONAL_DERIVED_OPS = {
    "cross_sectional_rank",
    "cross_sectional_zscore",
    "cross_sectional_demean",
    "group_cross_sectional_rank",
    "group_cross_sectional_zscore",
    "group_cross_sectional_demean",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def cross_sectional_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "cross_sectional_rank":
        rank = first.rank(method="ordinal", descending=True).over("ts")
        count = pl.len().over("ts")
        return (
            pl.when(count <= 1)
            .then(1.0)
            .otherwise(1.0 - ((rank - 1.0) / _safe_denominator(count - 1.0)))
        )
    if feature.op in {"cross_sectional_zscore", "cross_sectional_demean"}:
        mean = first.mean().over("ts")
        demeaned = first - mean
        if feature.op == "cross_sectional_demean":
            return demeaned
        return demeaned / _safe_denominator(first.std().over("ts"))
    if feature.op == "group_cross_sectional_rank":
        group = pl.col(feature.columns[1])
        rank = first.rank(method="ordinal", descending=True).over(["ts", group])
        count = pl.len().over(["ts", group])
        return (
            pl.when(count <= 1)
            .then(1.0)
            .otherwise(1.0 - ((rank - 1.0) / _safe_denominator(count - 1.0)))
        )
    group = pl.col(feature.columns[1])
    mean = first.mean().over(["ts", group])
    demeaned = first - mean
    if feature.op == "group_cross_sectional_demean":
        return demeaned
    return demeaned / _safe_denominator(first.std().over(["ts", group]))
