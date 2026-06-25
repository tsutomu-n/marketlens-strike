from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


RETURN_TRANSFORM_DERIVED_OPS = {
    "pct_change",
    "log_return",
    "lag",
    "rolling_return",
    "ewm_mean",
    "rsi",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def return_transform_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "pct_change":
        previous = first.shift(1).over("canonical_symbol")
        return (first - previous) / _safe_denominator(previous)
    if feature.op == "log_return":
        previous = first.shift(1).over("canonical_symbol")
        return (first / _safe_denominator(previous)).log()
    if feature.op == "lag":
        return first.shift(feature.window or 1).over("canonical_symbol")
    if feature.op == "rolling_return":
        previous = first.shift(feature.window or 1).over("canonical_symbol")
        return (first / _safe_denominator(previous)) - 1.0
    if feature.op == "ewm_mean":
        return first.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )

    delta = first.diff().over("canonical_symbol")
    gain = pl.when(delta > 0).then(delta).otherwise(0.0)
    loss = pl.when(delta < 0).then(-delta).otherwise(0.0)
    average_gain = gain.rolling_mean(
        window_size=feature.window or 1, min_samples=feature.window or 1
    ).over("canonical_symbol")
    average_loss = loss.rolling_mean(
        window_size=feature.window or 1, min_samples=feature.window or 1
    ).over("canonical_symbol")
    return (
        pl.when((average_loss == 0) & (average_gain > 0))
        .then(100.0)
        .when((average_loss == 0) & (average_gain == 0))
        .then(50.0)
        .otherwise(100.0 - (100.0 / (1.0 + (average_gain / average_loss))))
    )
