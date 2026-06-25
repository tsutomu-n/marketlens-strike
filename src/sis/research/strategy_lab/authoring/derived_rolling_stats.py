from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature

ROLLING_STAT_DERIVED_OPS = {
    "rolling_min",
    "rolling_max",
    "rolling_sum",
    "rolling_mean",
    "rolling_std",
    "rolling_zscore",
    "rolling_percentile_rank",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def rolling_stat_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    window = feature.window or 1

    if feature.op == "rolling_min":
        return first.rolling_min(window_size=window, min_samples=1).over("canonical_symbol")
    if feature.op == "rolling_max":
        return first.rolling_max(window_size=window, min_samples=1).over("canonical_symbol")
    if feature.op == "rolling_sum":
        return first.rolling_sum(window_size=window, min_samples=1).over("canonical_symbol")
    if feature.op == "rolling_mean":
        return first.rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
    if feature.op == "rolling_std":
        return first.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
    if feature.op == "rolling_zscore":
        mean = first.rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
        std = first.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
        return (first - mean) / _safe_denominator(std)
    return first.rolling_map(
        lambda values: (values <= values[-1]).sum() / len(values),
        window_size=window,
        min_samples=1,
    ).over("canonical_symbol")
