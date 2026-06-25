from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


LIQUIDITY_DERIVED_OPS = {
    "order_flow_imbalance",
    "liquidity_depth_ratio",
    "spread_bps",
    "funding_bps",
    "carry_adjusted_return",
    "vol_risk_premium",
    "put_call_skew",
    "liquidity_stress",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def liquidity_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "order_flow_imbalance":
        second = pl.col(feature.columns[1])
        return (first - second) / _safe_denominator(first + second)
    if feature.op == "liquidity_depth_ratio":
        second = pl.col(feature.columns[1])
        return first / _safe_denominator(second)
    if feature.op == "spread_bps":
        ask = pl.col(feature.columns[1])
        midpoint = (first + ask) / 2.0
        return (ask - first) / _safe_denominator(midpoint) * 10_000.0
    if feature.op == "funding_bps":
        return first * 10_000.0
    if feature.op in {"carry_adjusted_return", "vol_risk_premium", "put_call_skew"}:
        second = pl.col(feature.columns[1])
        return first - second
    ask = pl.col(feature.columns[1])
    depth = pl.col(feature.columns[2])
    midpoint = (first + ask) / 2.0
    spread_bps = (ask - first) / _safe_denominator(midpoint) * 10_000.0
    return spread_bps / _safe_denominator(depth)
