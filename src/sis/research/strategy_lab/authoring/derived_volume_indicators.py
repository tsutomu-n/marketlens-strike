from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


VOLUME_INDICATOR_DERIVED_OPS = {
    "obv",
    "volume_zscore",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def volume_indicator_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "obv":
        volume = pl.col(feature.columns[1])
        delta = first.diff().over("canonical_symbol")
        signed_volume = pl.when(delta > 0).then(volume).when(delta < 0).then(-volume).otherwise(0.0)
        return signed_volume.cum_sum().over("canonical_symbol")

    mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
        "canonical_symbol"
    )
    std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
        "canonical_symbol"
    )
    return (first - mean) / _safe_denominator(std)
