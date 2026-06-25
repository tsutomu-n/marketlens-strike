from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature

TREND_TRANSFORM_DERIVED_OPS = {
    "cumulative_return",
    "slope",
    "mean_reversion_score",
    "distance_from_ma",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def trend_transform_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    window = feature.window or 1

    if feature.op == "cumulative_return":
        return ((1.0 + first).cum_prod().over("canonical_symbol")) - 1.0
    if feature.op == "slope":
        previous = first.shift(window).over("canonical_symbol")
        return (first - previous) / float(window)
    if feature.op == "mean_reversion_score":
        mean = first.rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
        std = first.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
        return -((first - mean) / _safe_denominator(std))
    mean = first.rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
    return (first - mean) / _safe_denominator(mean.abs())
