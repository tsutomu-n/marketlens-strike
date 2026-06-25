from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


DRAWDOWN_DERIVED_OPS = {
    "drawdown_from_peak",
    "rolling_max_drawdown",
    "drawdown_duration",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def drawdown_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "drawdown_duration":
        return first.rolling_map(
            lambda values: len(values) - 1 - int(values.arg_max() or 0),
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")

    rolling_peak = first.rolling_max(window_size=feature.window or 1, min_samples=1).over(
        "canonical_symbol"
    )
    drawdown = (first / _safe_denominator(rolling_peak)) - 1.0
    if feature.op == "drawdown_from_peak":
        return drawdown
    return drawdown.rolling_min(window_size=feature.window or 1, min_samples=1).over(
        "canonical_symbol"
    )
