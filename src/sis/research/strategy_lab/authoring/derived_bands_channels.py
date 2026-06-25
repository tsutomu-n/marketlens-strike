from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


BANDS_CHANNEL_DERIVED_OPS = {
    "true_range",
    "atr",
    "bollinger_upper",
    "bollinger_lower",
    "bollinger_width",
    "bollinger_percent_b",
    "donchian_upper",
    "donchian_lower",
    "donchian_mid",
    "donchian_width",
    "keltner_upper",
    "keltner_lower",
    "keltner_width",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def _true_range(high: pl.Expr, low: pl.Expr, close: pl.Expr) -> pl.Expr:
    previous_close = close.shift(1).over("canonical_symbol")
    return pl.max_horizontal(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ]
    )


def bands_channel_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op in {"true_range", "atr"}:
        true_range = _true_range(first, pl.col(feature.columns[1]), pl.col(feature.columns[2]))
        if feature.op == "true_range":
            return true_range
        return true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )

    if feature.op.startswith("bollinger_"):
        multiplier = feature.value if feature.value is not None else 2.0
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        upper = mean + (std * multiplier)
        lower = mean - (std * multiplier)
        if feature.op == "bollinger_upper":
            return upper
        if feature.op == "bollinger_lower":
            return lower
        if feature.op == "bollinger_width":
            return (upper - lower) / _safe_denominator(mean)
        return (first - lower) / _safe_denominator(upper - lower)

    if feature.op.startswith("donchian_"):
        high = first
        low = pl.col(feature.columns[1])
        upper = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        lower = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        if feature.op == "donchian_upper":
            return upper
        if feature.op == "donchian_lower":
            return lower
        midpoint = (upper + lower) / 2.0
        if feature.op == "donchian_mid":
            return midpoint
        return (upper - lower) / _safe_denominator(midpoint)

    high = first
    low = pl.col(feature.columns[1])
    close = pl.col(feature.columns[2])
    multiplier = feature.value if feature.value is not None else 2.0
    true_range = _true_range(high, low, close)
    center = close.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
        "canonical_symbol"
    )
    atr = true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
        "canonical_symbol"
    )
    upper = center + (atr * multiplier)
    lower = center - (atr * multiplier)
    if feature.op == "keltner_upper":
        return upper
    if feature.op == "keltner_lower":
        return lower
    return (upper - lower) / _safe_denominator(center)
