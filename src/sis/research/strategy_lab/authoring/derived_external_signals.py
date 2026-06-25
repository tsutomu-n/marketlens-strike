from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


EXTERNAL_SIGNAL_DERIVED_OPS = {
    "net_exchange_flow",
    "onchain_activity_ratio",
    "sentiment_weighted_score",
    "event_surprise",
    "fundamental_value_gap",
    "risk_adjusted_score",
    "inverse_volatility_weight",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def external_signal_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "inverse_volatility_weight":
        return 1.0 / _safe_denominator(first)

    second = pl.col(feature.columns[1])
    if feature.op in {"net_exchange_flow", "event_surprise"}:
        return first - second
    if feature.op == "onchain_activity_ratio":
        return first / _safe_denominator(second)
    if feature.op == "sentiment_weighted_score":
        return first * second
    if feature.op == "fundamental_value_gap":
        return (first - second) / _safe_denominator(second)
    return first / _safe_denominator(second.abs())
