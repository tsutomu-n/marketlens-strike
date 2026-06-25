from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


TREND_INDICATOR_DERIVED_OPS = {
    "ichimoku_conversion",
    "ichimoku_base",
    "ichimoku_span_b",
    "ichimoku_span_a",
    "macd_line",
    "stochastic_k",
    "stochastic_d",
    "adx",
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


def _midpoint_channel(high: pl.Expr, low: pl.Expr, window: int) -> pl.Expr:
    high_max = high.rolling_max(window_size=window, min_samples=1).over("canonical_symbol")
    low_min = low.rolling_min(window_size=window, min_samples=1).over("canonical_symbol")
    return (high_max + low_min) / 2.0


def trend_indicator_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op in {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_b"}:
        return _midpoint_channel(first, pl.col(feature.columns[1]), feature.window or 1)
    if feature.op == "ichimoku_span_a":
        return (first + pl.col(feature.columns[1])) / 2.0
    if feature.op == "macd_line":
        fast = first.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )
        slow_span = int(feature.value or 1)
        slow = first.ewm_mean(span=slow_span, adjust=False, min_samples=1).over("canonical_symbol")
        return fast - slow
    if feature.op == "stochastic_d":
        return first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )

    high = first
    low = pl.col(feature.columns[1])
    close = pl.col(feature.columns[2])
    if feature.op == "stochastic_k":
        low_min = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        high_max = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        return 100.0 * (close - low_min) / _safe_denominator(high_max - low_min)

    true_range = _true_range(high, low, close)
    up_move = high - high.shift(1).over("canonical_symbol")
    down_move = low.shift(1).over("canonical_symbol") - low
    plus_dm = pl.when((up_move > down_move) & (up_move > 0.0)).then(up_move).otherwise(0.0)
    minus_dm = pl.when((down_move > up_move) & (down_move > 0.0)).then(down_move).otherwise(0.0)
    atr = true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
        "canonical_symbol"
    )
    plus_di = (
        100.0
        * plus_dm.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        / _safe_denominator(atr)
    )
    minus_di = (
        100.0
        * minus_dm.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        / _safe_denominator(atr)
    )
    dx = 100.0 * (plus_di - minus_di).abs() / _safe_denominator(plus_di + minus_di)
    return dx.rolling_mean(window_size=feature.window or 1, min_samples=1).over("canonical_symbol")
