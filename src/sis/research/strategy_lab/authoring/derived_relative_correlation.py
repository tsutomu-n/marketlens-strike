from __future__ import annotations

import math

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature

RELATIVE_CORRELATION_DERIVED_OPS = {
    "rolling_corr",
    "rolling_beta",
    "rolling_spread_zscore",
    "tracking_error",
    "information_ratio",
    "rolling_autocorr",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def _rolling_covariance_parts(
    first: pl.Expr, second: pl.Expr, window: int
) -> tuple[pl.Expr, pl.Expr, pl.Expr]:
    mean_first = first.rolling_mean(window_size=window, min_samples=2).over("canonical_symbol")
    mean_second = second.rolling_mean(window_size=window, min_samples=2).over("canonical_symbol")
    mean_product = (
        (first * second).rolling_mean(window_size=window, min_samples=2).over("canonical_symbol")
    )
    covariance = mean_product - (mean_first * mean_second)
    return mean_first, mean_second, covariance


def relative_correlation_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    window = feature.window or 1

    if feature.op == "rolling_autocorr":
        lagged = first.shift(1).over("canonical_symbol")
        mean_first, mean_lagged, covariance = _rolling_covariance_parts(first, lagged, window)
        variance_first = (first * first).rolling_mean(window_size=window, min_samples=2).over(
            "canonical_symbol"
        ) - (mean_first * mean_first)
        variance_lagged = (lagged * lagged).rolling_mean(window_size=window, min_samples=2).over(
            "canonical_symbol"
        ) - (mean_lagged * mean_lagged)
        return covariance / _safe_denominator((variance_first * variance_lagged).sqrt())

    second = pl.col(feature.columns[1])
    if feature.op == "rolling_spread_zscore":
        spread = first - second
        mean = spread.rolling_mean(window_size=window, min_samples=1).over("canonical_symbol")
        std = spread.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
        return (spread - mean) / _safe_denominator(std)
    if feature.op in {"tracking_error", "information_ratio"}:
        active_return = first - second
        periods = feature.value if feature.value is not None else 252.0
        annualization = math.sqrt(periods)
        tracking_error = (
            active_return.rolling_std(window_size=window, min_samples=2).over("canonical_symbol")
            * annualization
        )
        if feature.op == "tracking_error":
            return tracking_error
        active_mean = active_return.rolling_mean(window_size=window, min_samples=1).over(
            "canonical_symbol"
        )
        return (active_mean * periods) / _safe_denominator(tracking_error)

    mean_first, mean_second, covariance = _rolling_covariance_parts(first, second, window)
    variance_second = (second * second).rolling_mean(window_size=window, min_samples=2).over(
        "canonical_symbol"
    ) - (mean_second * mean_second)
    if feature.op == "rolling_beta":
        return covariance / _safe_denominator(variance_second)
    variance_first = (first * first).rolling_mean(window_size=window, min_samples=2).over(
        "canonical_symbol"
    ) - (mean_first * mean_first)
    return covariance / _safe_denominator((variance_first * variance_second).sqrt())
