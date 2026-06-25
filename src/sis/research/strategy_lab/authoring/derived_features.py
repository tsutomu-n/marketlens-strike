from __future__ import annotations

import math

import polars as pl

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.derived_bands_channels import (
    BANDS_CHANNEL_DERIVED_OPS,
    bands_channel_expression,
)
from sis.research.strategy_lab.authoring.derived_cross_sectional import (
    CROSS_SECTIONAL_DERIVED_OPS,
    cross_sectional_expression,
)
from sis.research.strategy_lab.authoring.derived_drawdown import (
    DRAWDOWN_DERIVED_OPS,
    drawdown_expression,
)
from sis.research.strategy_lab.authoring.derived_execution_costs import (
    EXECUTION_COST_DERIVED_OPS,
    execution_cost_expression,
)
from sis.research.strategy_lab.authoring.derived_external_signals import (
    EXTERNAL_SIGNAL_DERIVED_OPS,
    external_signal_expression,
)
from sis.research.strategy_lab.authoring.derived_liquidity import (
    LIQUIDITY_DERIVED_OPS,
    liquidity_expression,
)
from sis.research.strategy_lab.authoring.derived_quality import (
    QUALITY_DERIVED_OPS,
    quality_expression,
)
from sis.research.strategy_lab.authoring.derived_trend_indicators import (
    TREND_INDICATOR_DERIVED_OPS,
    trend_indicator_expression,
)
from sis.research.strategy_lab.authoring.derived_volume_indicators import (
    VOLUME_INDICATOR_DERIVED_OPS,
    volume_indicator_expression,
)


def literal_or_col(feature: DerivedFeature, index: int = 1) -> pl.Expr:
    if len(feature.columns) > index:
        return pl.col(feature.columns[index])
    if feature.value is None:
        raise StrategyAuthoringValidationError(
            f"derived feature {feature.name} requires column {index + 1} or value"
        )
    return pl.lit(feature.value)


def safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def derived_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "add":
        expr = first
        for column in feature.columns[1:]:
            expr = expr + pl.col(column)
        if feature.value is not None:
            expr = expr + feature.value
    elif feature.op == "sub":
        expr = first - literal_or_col(feature)
    elif feature.op == "mul":
        expr = first
        for column in feature.columns[1:]:
            expr = expr * pl.col(column)
        if feature.value is not None:
            expr = expr * feature.value
    elif feature.op in {"div", "ratio"}:
        denominator = literal_or_col(feature)
        expr = first / safe_denominator(denominator)
    elif feature.op == "diff":
        expr = first - literal_or_col(feature)
    elif feature.op == "pct_diff":
        denominator = literal_or_col(feature)
        expr = (first - denominator) / safe_denominator(denominator)
    elif feature.op == "abs":
        expr = first.abs()
    elif feature.op == "neg":
        expr = -first
    elif feature.op == "max":
        expr = pl.max_horizontal([pl.col(column) for column in feature.columns])
        if feature.value is not None:
            expr = pl.max_horizontal([expr, pl.lit(feature.value)])
    elif feature.op == "min":
        expr = pl.min_horizontal([pl.col(column) for column in feature.columns])
        if feature.value is not None:
            expr = pl.min_horizontal([expr, pl.lit(feature.value)])
    elif feature.op == "mean":
        expressions = [pl.col(column) for column in feature.columns]
        if feature.value is not None:
            expressions.append(pl.lit(feature.value))
        expr = pl.mean_horizontal(expressions)
    elif feature.op in BANDS_CHANNEL_DERIVED_OPS:
        expr = bands_channel_expression(feature)
    elif feature.op in TREND_INDICATOR_DERIVED_OPS:
        expr = trend_indicator_expression(feature)
    elif feature.op in VOLUME_INDICATOR_DERIVED_OPS:
        expr = volume_indicator_expression(feature)
    elif feature.op == "ts_weekday":
        expr = first.dt.weekday() - 1
    elif feature.op == "ts_hour":
        expr = first.dt.hour()
    elif feature.op == "ts_month":
        expr = first.dt.month()
    elif feature.op == "ts_day":
        expr = first.dt.day()
    elif feature.op == "pct_change":
        previous = first.shift(1).over("canonical_symbol")
        expr = (first - previous) / safe_denominator(previous)
    elif feature.op == "log_return":
        previous = first.shift(1).over("canonical_symbol")
        expr = (first / safe_denominator(previous)).log()
    elif feature.op == "lag":
        expr = first.shift(feature.window or 1).over("canonical_symbol")
    elif feature.op == "rolling_return":
        previous = first.shift(feature.window or 1).over("canonical_symbol")
        expr = (first / safe_denominator(previous)) - 1.0
    elif feature.op == "ewm_mean":
        expr = first.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rsi":
        delta = first.diff().over("canonical_symbol")
        gain = pl.when(delta > 0).then(delta).otherwise(0.0)
        loss = pl.when(delta < 0).then(-delta).otherwise(0.0)
        average_gain = gain.rolling_mean(
            window_size=feature.window or 1, min_samples=feature.window or 1
        ).over("canonical_symbol")
        average_loss = loss.rolling_mean(
            window_size=feature.window or 1, min_samples=feature.window or 1
        ).over("canonical_symbol")
        expr = (
            pl.when((average_loss == 0) & (average_gain > 0))
            .then(100.0)
            .when((average_loss == 0) & (average_gain == 0))
            .then(50.0)
            .otherwise(100.0 - (100.0 / (1.0 + (average_gain / average_loss))))
        )
    elif feature.op == "rolling_min":
        expr = first.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_max":
        expr = first.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_sum":
        expr = first.rolling_sum(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_mean":
        expr = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_std":
        expr = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_zscore":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        expr = (first - mean) / safe_denominator(std)
    elif feature.op == "rolling_percentile_rank":
        expr = first.rolling_map(
            lambda values: (values <= values[-1]).sum() / len(values),
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "rolling_volatility":
        expr = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_skew":
        expr = first.rolling_skew(window_size=feature.window or 1, min_samples=3).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_kurtosis":
        expr = first.rolling_kurtosis(window_size=feature.window or 1, min_samples=4).over(
            "canonical_symbol"
        )
    elif feature.op == "annualized_volatility":
        periods = math.sqrt(feature.value if feature.value is not None else 252.0)
        expr = (
            first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            * periods
        )
    elif feature.op == "realized_variance":
        expr = (
            (first * first)
            .rolling_mean(window_size=feature.window or 1, min_samples=1)
            .over("canonical_symbol")
        )
    elif feature.op == "downside_volatility":
        downside = pl.when(first < 0.0).then(first).otherwise(0.0)
        expr = downside.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
    elif feature.op in {"sharpe_like", "sortino_like"}:
        periods = math.sqrt(feature.value if feature.value is not None else 252.0)
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        if feature.op == "sharpe_like":
            risk = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
        else:
            downside = pl.when(first < 0.0).then(first).otherwise(0.0)
            risk = downside.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
        expr = mean / safe_denominator(risk) * periods
    elif feature.op == "kelly_fraction":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        variance = (
            first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            ** 2
        )
        expr = mean / safe_denominator(variance)
    elif feature.op == "historical_var":
        alpha = feature.value if feature.value is not None else 0.05
        expr = -first.rolling_quantile(
            quantile=alpha,
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "expected_shortfall":
        alpha = feature.value if feature.value is not None else 0.05
        var_threshold = first.rolling_quantile(
            quantile=alpha,
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
        tail_return = pl.when(first <= var_threshold).then(first).otherwise(None)
        expr = -tail_return.rolling_mean(
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "cumulative_return":
        expr = ((1.0 + first).cum_prod().over("canonical_symbol")) - 1.0
    elif feature.op == "slope":
        previous = first.shift(feature.window or 1).over("canonical_symbol")
        expr = (first - previous) / float(feature.window or 1)
    elif feature.op == "mean_reversion_score":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        expr = -((first - mean) / safe_denominator(std))
    elif feature.op == "distance_from_ma":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        expr = (first - mean) / safe_denominator(mean.abs())
    elif feature.op in {
        "rolling_corr",
        "rolling_beta",
        "rolling_spread_zscore",
        "tracking_error",
        "information_ratio",
    }:
        second = pl.col(feature.columns[1])
        if feature.op == "rolling_spread_zscore":
            spread = first - second
            mean = spread.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            std = spread.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            expr = (spread - mean) / safe_denominator(std)
        elif feature.op in {"tracking_error", "information_ratio"}:
            active_return = first - second
            periods = feature.value if feature.value is not None else 252.0
            annualization = math.sqrt(periods)
            tracking_error = (
                active_return.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                    "canonical_symbol"
                )
                * annualization
            )
            if feature.op == "tracking_error":
                expr = tracking_error
            else:
                active_mean = active_return.rolling_mean(
                    window_size=feature.window or 1, min_samples=1
                ).over("canonical_symbol")
                expr = (active_mean * periods) / safe_denominator(tracking_error)
        else:
            mean_first = first.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            mean_second = second.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            mean_product = (
                (first * second)
                .rolling_mean(window_size=feature.window or 1, min_samples=2)
                .over("canonical_symbol")
            )
            covariance = mean_product - (mean_first * mean_second)
            variance_second = (second * second).rolling_mean(
                window_size=feature.window or 1, min_samples=2
            ).over("canonical_symbol") - (mean_second * mean_second)
            if feature.op == "rolling_beta":
                expr = covariance / safe_denominator(variance_second)
            else:
                variance_first = (first * first).rolling_mean(
                    window_size=feature.window or 1, min_samples=2
                ).over("canonical_symbol") - (mean_first * mean_first)
                expr = covariance / safe_denominator((variance_first * variance_second).sqrt())
    elif feature.op == "rolling_autocorr":
        lagged = first.shift(1).over("canonical_symbol")
        mean_first = first.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        mean_lagged = lagged.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        mean_product = (
            (first * lagged)
            .rolling_mean(window_size=feature.window or 1, min_samples=2)
            .over("canonical_symbol")
        )
        covariance = mean_product - (mean_first * mean_lagged)
        variance_first = (first * first).rolling_mean(
            window_size=feature.window or 1, min_samples=2
        ).over("canonical_symbol") - (mean_first * mean_first)
        variance_lagged = (lagged * lagged).rolling_mean(
            window_size=feature.window or 1, min_samples=2
        ).over("canonical_symbol") - (mean_lagged * mean_lagged)
        expr = covariance / safe_denominator((variance_first * variance_lagged).sqrt())
    elif feature.op in LIQUIDITY_DERIVED_OPS:
        expr = liquidity_expression(feature)
    elif feature.op in EXTERNAL_SIGNAL_DERIVED_OPS:
        expr = external_signal_expression(feature)
    elif feature.op in CROSS_SECTIONAL_DERIVED_OPS:
        expr = cross_sectional_expression(feature)
    elif feature.op in EXECUTION_COST_DERIVED_OPS:
        expr = execution_cost_expression(feature)
    elif feature.op in QUALITY_DERIVED_OPS:
        expr = quality_expression(feature)
    elif feature.op in DRAWDOWN_DERIVED_OPS:
        expr = drawdown_expression(feature)
    else:
        raise StrategyAuthoringValidationError(f"Unsupported derived feature op: {feature.op}")
    if feature.fill_null is not None:
        expr = expr.fill_null(feature.fill_null)
    return expr.alias(feature.name)


def apply_derived_features(frame: pl.DataFrame, spec: StrategyAuthoringSpec) -> pl.DataFrame:
    if not spec.rules.derived_features:
        return frame
    derived = frame.sort(["canonical_symbol", "ts"])
    for feature in spec.rules.derived_features:
        derived = derived.with_columns(derived_expression(feature))
    return derived
