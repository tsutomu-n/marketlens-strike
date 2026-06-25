from __future__ import annotations

import math

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature

ROLLING_RISK_STAT_DERIVED_OPS = {
    "rolling_volatility",
    "rolling_skew",
    "rolling_kurtosis",
    "annualized_volatility",
    "realized_variance",
    "downside_volatility",
    "sharpe_like",
    "sortino_like",
    "kelly_fraction",
    "historical_var",
    "expected_shortfall",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def rolling_risk_stat_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    window = feature.window or 1

    if feature.op == "rolling_volatility":
        return first.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
    if feature.op == "rolling_skew":
        return first.rolling_skew(window_size=window, min_samples=3).over("canonical_symbol")
    if feature.op == "rolling_kurtosis":
        return first.rolling_kurtosis(window_size=window, min_samples=4).over("canonical_symbol")
    if feature.op == "annualized_volatility":
        periods = math.sqrt(feature.value if feature.value is not None else 252.0)
        return (
            first.rolling_std(window_size=window, min_samples=2).over("canonical_symbol") * periods
        )
    if feature.op == "realized_variance":
        return (
            (first * first).rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
        )
    if feature.op == "downside_volatility":
        downside = pl.when(first < 0.0).then(first).otherwise(0.0)
        return downside.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
    if feature.op in {"sharpe_like", "sortino_like"}:
        periods = math.sqrt(feature.value if feature.value is not None else 252.0)
        mean = first.rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
        if feature.op == "sharpe_like":
            risk = first.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
        else:
            downside = pl.when(first < 0.0).then(first).otherwise(0.0)
            risk = downside.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
        return mean / _safe_denominator(risk) * periods
    if feature.op == "kelly_fraction":
        mean = first.rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
        variance = (
            first.rolling_std(window_size=window, min_samples=2).over("canonical_symbol") ** 2
        )
        return mean / _safe_denominator(variance)
    if feature.op == "historical_var":
        alpha = feature.value if feature.value is not None else 0.05
        return -first.rolling_quantile(
            quantile=alpha,
            window_size=window,
            min_samples=1,
        ).over("canonical_symbol")
    alpha = feature.value if feature.value is not None else 0.05
    var_threshold = first.rolling_quantile(
        quantile=alpha,
        window_size=window,
        min_samples=1,
    ).over("canonical_symbol")
    tail_return = pl.when(first <= var_threshold).then(first).otherwise(None)
    return -tail_return.rolling_mean(
        window_size=window,
        min_samples=1,
    ).over("canonical_symbol")
