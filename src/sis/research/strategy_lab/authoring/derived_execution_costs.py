from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


EXECUTION_COST_DERIVED_OPS = {
    "queue_position_score",
    "latency_penalty_bps",
    "maker_taker_fee_edge_bps",
    "borrow_cost_bps",
    "borrow_availability_ratio",
    "tax_drag_bps",
    "rebalance_drift",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def execution_cost_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "queue_position_score":
        second = pl.col(feature.columns[1])
        return 1.0 - (first / _safe_denominator(first + second))
    if feature.op == "latency_penalty_bps":
        multiplier = feature.value if feature.value is not None else 1.0
        return first * multiplier
    if feature.op == "maker_taker_fee_edge_bps":
        second = pl.col(feature.columns[1])
        return second - first
    if feature.op == "borrow_cost_bps":
        second = pl.col(feature.columns[1])
        return first * second * 10_000.0
    if feature.op == "borrow_availability_ratio":
        second = pl.col(feature.columns[1])
        return first / _safe_denominator(second)
    if feature.op == "tax_drag_bps":
        second = pl.col(feature.columns[1])
        return first * second * 10_000.0
    second = pl.col(feature.columns[1])
    return (first - second).abs()
