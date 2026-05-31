from __future__ import annotations

import math
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.contracts import (
    Condition,
    DerivedFeature,
    StrategyAuthoringSpec,
    StrategyAuthoringValidationError,
    _stable_digest,
)
from sis.research.strategy_lab.authoring.validation import _all_conditions

ADVANCED_CONDITION_OPERATORS = {
    "crosses_above",
    "crosses_below",
    "rising",
    "falling",
    "consecutive_gt",
    "consecutive_gte",
    "consecutive_lt",
    "consecutive_lte",
    "consecutive_eq",
    "consecutive_neq",
}


def _condition_feature_name(condition: Condition) -> str:
    payload = condition.model_dump(mode="json", exclude_none=True)
    return f"__condition_{_stable_digest(payload)}"


def _condition_target_expr(condition: Condition) -> pl.Expr:
    return (
        pl.col(condition.value_column)
        if condition.value_column is not None
        else pl.lit(condition.value)
    )


def _condition_comparison_expr(condition: Condition) -> pl.Expr:
    target = _condition_target_expr(condition)
    value = pl.col(condition.column)
    op = condition.op.removeprefix("consecutive_")
    if op == "gt":
        return value > target
    if op == "gte":
        return value >= target
    if op == "lt":
        return value < target
    if op == "lte":
        return value <= target
    if op == "eq":
        return value == target
    if op == "neq":
        return value != target
    raise StrategyAuthoringValidationError(f"Unsupported advanced comparison: {condition.op}")


def _condition_feature_expr(condition: Condition) -> pl.Expr:
    value = pl.col(condition.column)
    if condition.op in {"crosses_above", "crosses_below"}:
        target = _condition_target_expr(condition)
        previous_value = value.shift(1).over("canonical_symbol")
        previous_target = (
            pl.col(condition.value_column).shift(1).over("canonical_symbol")
            if condition.value_column is not None
            else pl.lit(condition.value)
        )
        if condition.op == "crosses_above":
            expr = (value > target) & (previous_value <= previous_target)
        else:
            expr = (value < target) & (previous_value >= previous_target)
    elif condition.op in {"rising", "falling"}:
        previous_value = value.shift(condition.window or 1).over("canonical_symbol")
        expr = value > previous_value if condition.op == "rising" else value < previous_value
    elif condition.op.startswith("consecutive_"):
        base = _condition_comparison_expr(condition).cast(pl.Int8)
        expr = (
            base.rolling_min(window_size=condition.window or 1, min_samples=condition.window or 1)
            .over("canonical_symbol")
            .fill_null(0)
            == 1
        )
    else:
        raise StrategyAuthoringValidationError(f"Unsupported advanced condition: {condition.op}")
    return expr.fill_null(False).alias(_condition_feature_name(condition))


def _apply_condition_features(frame: pl.DataFrame, spec: StrategyAuthoringSpec) -> pl.DataFrame:
    conditions = [
        condition
        for condition in _all_conditions(spec)
        if condition.op in ADVANCED_CONDITION_OPERATORS
    ]
    if not conditions:
        return frame
    enriched = frame.sort(["canonical_symbol", "ts"])
    seen: set[str] = set()
    for condition in conditions:
        name = _condition_feature_name(condition)
        if name in seen:
            continue
        seen.add(name)
        enriched = enriched.with_columns(_condition_feature_expr(condition))
    return enriched


def _condition_passes(row: dict[str, Any], condition: Condition) -> bool:
    if condition.op in ADVANCED_CONDITION_OPERATORS:
        return bool(row.get(_condition_feature_name(condition)))
    value = row.get(condition.column)
    if condition.op == "is_true":
        return value is True
    if condition.op == "is_false":
        return value is False
    if value is None:
        return False
    target = (
        row.get(condition.value_column) if condition.value_column is not None else condition.value
    )
    if target is None:
        return False
    if condition.op == "gt":
        return value > target
    if condition.op == "gte":
        return value >= target
    if condition.op == "lt":
        return value < target
    if condition.op == "lte":
        return value <= target
    if condition.op == "eq":
        return value == target
    if condition.op == "neq":
        return value != target
    if condition.op == "between":
        low, high = target
        return low <= value <= high
    if condition.op == "in":
        return value in target
    if condition.op == "not_in":
        return value not in target
    raise StrategyAuthoringValidationError(f"Unsupported operator: {condition.op}")


def _literal_or_col(feature: DerivedFeature, index: int = 1) -> pl.Expr:
    if len(feature.columns) > index:
        return pl.col(feature.columns[index])
    if feature.value is None:
        raise StrategyAuthoringValidationError(
            f"derived feature {feature.name} requires column {index + 1} or value"
        )
    return pl.lit(feature.value)


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def _derived_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "add":
        expr = first
        for column in feature.columns[1:]:
            expr = expr + pl.col(column)
        if feature.value is not None:
            expr = expr + feature.value
    elif feature.op == "sub":
        expr = first - _literal_or_col(feature)
    elif feature.op == "mul":
        expr = first
        for column in feature.columns[1:]:
            expr = expr * pl.col(column)
        if feature.value is not None:
            expr = expr * feature.value
    elif feature.op in {"div", "ratio"}:
        denominator = _literal_or_col(feature)
        expr = first / _safe_denominator(denominator)
    elif feature.op == "diff":
        expr = first - _literal_or_col(feature)
    elif feature.op == "pct_diff":
        denominator = _literal_or_col(feature)
        expr = (first - denominator) / _safe_denominator(denominator)
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
    elif feature.op in {"true_range", "atr"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        close = pl.col(feature.columns[2])
        previous_close = close.shift(1).over("canonical_symbol")
        true_range = pl.max_horizontal(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ]
        )
        expr = (
            true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            if feature.op == "atr"
            else true_range
        )
    elif feature.op in {
        "bollinger_upper",
        "bollinger_lower",
        "bollinger_width",
        "bollinger_percent_b",
    }:
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
            expr = upper
        elif feature.op == "bollinger_lower":
            expr = lower
        elif feature.op == "bollinger_width":
            expr = (upper - lower) / _safe_denominator(mean)
        else:
            expr = (first - lower) / _safe_denominator(upper - lower)
    elif feature.op in {"donchian_upper", "donchian_lower", "donchian_mid", "donchian_width"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        upper = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        lower = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        if feature.op == "donchian_upper":
            expr = upper
        elif feature.op == "donchian_lower":
            expr = lower
        elif feature.op == "donchian_mid":
            expr = (upper + lower) / 2.0
        else:
            expr = (upper - lower) / _safe_denominator((upper + lower) / 2.0)
    elif feature.op in {"keltner_upper", "keltner_lower", "keltner_width"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        close = pl.col(feature.columns[2])
        multiplier = feature.value if feature.value is not None else 2.0
        previous_close = close.shift(1).over("canonical_symbol")
        true_range = pl.max_horizontal(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ]
        )
        center = close.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )
        atr = true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        upper = center + (atr * multiplier)
        lower = center - (atr * multiplier)
        if feature.op == "keltner_upper":
            expr = upper
        elif feature.op == "keltner_lower":
            expr = lower
        else:
            expr = (upper - lower) / _safe_denominator(center)
    elif feature.op in {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_b"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        high_max = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        low_min = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        expr = (high_max + low_min) / 2.0
    elif feature.op == "ichimoku_span_a":
        expr = (pl.col(feature.columns[0]) + pl.col(feature.columns[1])) / 2.0
    elif feature.op == "macd_line":
        fast = first.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )
        slow_span = int(feature.value or 1)
        slow = first.ewm_mean(span=slow_span, adjust=False, min_samples=1).over("canonical_symbol")
        expr = fast - slow
    elif feature.op in {"stochastic_k", "adx"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        close = pl.col(feature.columns[2])
        if feature.op == "stochastic_k":
            low_min = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            high_max = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            expr = 100.0 * (close - low_min) / _safe_denominator(high_max - low_min)
        else:
            previous_close = close.shift(1).over("canonical_symbol")
            true_range = pl.max_horizontal(
                [
                    high - low,
                    (high - previous_close).abs(),
                    (low - previous_close).abs(),
                ]
            )
            up_move = high - high.shift(1).over("canonical_symbol")
            down_move = low.shift(1).over("canonical_symbol") - low
            plus_dm = pl.when((up_move > down_move) & (up_move > 0.0)).then(up_move).otherwise(0.0)
            minus_dm = (
                pl.when((down_move > up_move) & (down_move > 0.0)).then(down_move).otherwise(0.0)
            )
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
            expr = dx.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
    elif feature.op == "stochastic_d":
        expr = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "obv":
        close = pl.col(feature.columns[0])
        volume = pl.col(feature.columns[1])
        delta = close.diff().over("canonical_symbol")
        signed_volume = pl.when(delta > 0).then(volume).when(delta < 0).then(-volume).otherwise(0.0)
        expr = signed_volume.cum_sum().over("canonical_symbol")
    elif feature.op == "volume_zscore":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        expr = (first - mean) / _safe_denominator(std)
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
        expr = (first - previous) / _safe_denominator(previous)
    elif feature.op == "log_return":
        previous = first.shift(1).over("canonical_symbol")
        expr = (first / _safe_denominator(previous)).log()
    elif feature.op == "lag":
        expr = first.shift(feature.window or 1).over("canonical_symbol")
    elif feature.op == "rolling_return":
        previous = first.shift(feature.window or 1).over("canonical_symbol")
        expr = (first / _safe_denominator(previous)) - 1.0
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
        expr = (first - mean) / _safe_denominator(std)
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
        expr = mean / _safe_denominator(risk) * periods
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
        expr = mean / _safe_denominator(variance)
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
        expr = -((first - mean) / _safe_denominator(std))
    elif feature.op == "distance_from_ma":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        expr = (first - mean) / _safe_denominator(mean.abs())
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
            expr = (spread - mean) / _safe_denominator(std)
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
                expr = (active_mean * periods) / _safe_denominator(tracking_error)
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
                expr = covariance / _safe_denominator(variance_second)
            else:
                variance_first = (first * first).rolling_mean(
                    window_size=feature.window or 1, min_samples=2
                ).over("canonical_symbol") - (mean_first * mean_first)
                expr = covariance / _safe_denominator((variance_first * variance_second).sqrt())
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
        expr = covariance / _safe_denominator((variance_first * variance_lagged).sqrt())
    elif feature.op == "order_flow_imbalance":
        second = pl.col(feature.columns[1])
        expr = (first - second) / _safe_denominator(first + second)
    elif feature.op == "liquidity_depth_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "spread_bps":
        ask = pl.col(feature.columns[1])
        midpoint = (first + ask) / 2.0
        expr = (ask - first) / _safe_denominator(midpoint) * 10_000.0
    elif feature.op == "funding_bps":
        expr = first * 10_000.0
    elif feature.op == "carry_adjusted_return":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "vol_risk_premium":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "put_call_skew":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "liquidity_stress":
        ask = pl.col(feature.columns[1])
        depth = pl.col(feature.columns[2])
        midpoint = (first + ask) / 2.0
        spread_bps = (ask - first) / _safe_denominator(midpoint) * 10_000.0
        expr = spread_bps / _safe_denominator(depth)
    elif feature.op == "net_exchange_flow":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "onchain_activity_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "sentiment_weighted_score":
        second = pl.col(feature.columns[1])
        expr = first * second
    elif feature.op == "event_surprise":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "fundamental_value_gap":
        second = pl.col(feature.columns[1])
        expr = (first - second) / _safe_denominator(second)
    elif feature.op == "risk_adjusted_score":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second.abs())
    elif feature.op == "inverse_volatility_weight":
        expr = 1.0 / _safe_denominator(first)
    elif feature.op == "cross_sectional_rank":
        rank = first.rank(method="ordinal", descending=True).over("ts")
        count = pl.len().over("ts")
        expr = (
            pl.when(count <= 1)
            .then(1.0)
            .otherwise(1.0 - ((rank - 1.0) / _safe_denominator(count - 1.0)))
        )
    elif feature.op in {"cross_sectional_zscore", "cross_sectional_demean"}:
        mean = first.mean().over("ts")
        demeaned = first - mean
        if feature.op == "cross_sectional_demean":
            expr = demeaned
        else:
            expr = demeaned / _safe_denominator(first.std().over("ts"))
    elif feature.op == "group_cross_sectional_rank":
        group = pl.col(feature.columns[1])
        rank = first.rank(method="ordinal", descending=True).over(["ts", group])
        count = pl.len().over(["ts", group])
        expr = (
            pl.when(count <= 1)
            .then(1.0)
            .otherwise(1.0 - ((rank - 1.0) / _safe_denominator(count - 1.0)))
        )
    elif feature.op in {"group_cross_sectional_zscore", "group_cross_sectional_demean"}:
        group = pl.col(feature.columns[1])
        mean = first.mean().over(["ts", group])
        demeaned = first - mean
        if feature.op == "group_cross_sectional_demean":
            expr = demeaned
        else:
            expr = demeaned / _safe_denominator(first.std().over(["ts", group]))
    elif feature.op == "queue_position_score":
        second = pl.col(feature.columns[1])
        expr = 1.0 - (first / _safe_denominator(first + second))
    elif feature.op == "latency_penalty_bps":
        multiplier = feature.value if feature.value is not None else 1.0
        expr = first * multiplier
    elif feature.op == "maker_taker_fee_edge_bps":
        second = pl.col(feature.columns[1])
        expr = second - first
    elif feature.op == "borrow_cost_bps":
        second = pl.col(feature.columns[1])
        expr = first * second * 10_000.0
    elif feature.op == "borrow_availability_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "tax_drag_bps":
        second = pl.col(feature.columns[1])
        expr = first * second * 10_000.0
    elif feature.op == "rebalance_drift":
        second = pl.col(feature.columns[1])
        expr = (first - second).abs()
    elif feature.op == "freshness_score":
        max_age = feature.value if feature.value is not None else 1.0
        raw = 1.0 - (first / _safe_denominator(pl.lit(max_age)))
        expr = pl.when(raw < 0.0).then(0.0).when(raw > 1.0).then(1.0).otherwise(raw)
    elif feature.op == "staleness_bps":
        multiplier = feature.value if feature.value is not None else 1.0
        expr = first * multiplier
    elif feature.op == "data_quality_blend":
        expr = pl.mean_horizontal([pl.col(column) for column in feature.columns])
    elif feature.op == "ensemble_vote_count":
        expr = pl.sum_horizontal([pl.col(column) for column in feature.columns])
    elif feature.op == "ensemble_vote_ratio":
        expr = pl.mean_horizontal([pl.col(column) for column in feature.columns])
    elif feature.op == "regime_transition_score":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "drawdown_from_peak":
        rolling_peak = first.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        expr = (first / _safe_denominator(rolling_peak)) - 1.0
    elif feature.op == "rolling_max_drawdown":
        rolling_peak = first.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        drawdown = (first / _safe_denominator(rolling_peak)) - 1.0
        expr = drawdown.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "drawdown_duration":
        expr = first.rolling_map(
            lambda values: len(values) - 1 - int(values.arg_max() or 0),
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "turnover_pressure":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "capacity_usage_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "correlation_crowding_score":
        second = pl.col(feature.columns[1])
        expr = first * second
    else:
        raise StrategyAuthoringValidationError(f"Unsupported derived feature op: {feature.op}")
    if feature.fill_null is not None:
        expr = expr.fill_null(feature.fill_null)
    return expr.alias(feature.name)


def _apply_derived_features(frame: pl.DataFrame, spec: StrategyAuthoringSpec) -> pl.DataFrame:
    if not spec.rules.derived_features:
        return frame
    derived = frame.sort(["canonical_symbol", "ts"])
    for feature in spec.rules.derived_features:
        derived = derived.with_columns(_derived_expression(feature))
    return derived
