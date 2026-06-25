from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


QUALITY_DERIVED_OPS = {
    "freshness_score",
    "staleness_bps",
    "data_quality_blend",
    "ensemble_vote_count",
    "ensemble_vote_ratio",
    "regime_transition_score",
    "turnover_pressure",
    "capacity_usage_ratio",
    "correlation_crowding_score",
}


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def quality_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "freshness_score":
        max_age = feature.value if feature.value is not None else 1.0
        raw = 1.0 - (first / _safe_denominator(pl.lit(max_age)))
        return pl.when(raw < 0.0).then(0.0).when(raw > 1.0).then(1.0).otherwise(raw)
    if feature.op == "staleness_bps":
        multiplier = feature.value if feature.value is not None else 1.0
        return first * multiplier
    if feature.op == "data_quality_blend":
        return pl.mean_horizontal([pl.col(column) for column in feature.columns])
    if feature.op == "ensemble_vote_count":
        return pl.sum_horizontal([pl.col(column) for column in feature.columns])
    if feature.op == "ensemble_vote_ratio":
        return pl.mean_horizontal([pl.col(column) for column in feature.columns])
    if feature.op == "regime_transition_score":
        second = pl.col(feature.columns[1])
        return first - second
    if feature.op in {"turnover_pressure", "capacity_usage_ratio"}:
        second = pl.col(feature.columns[1])
        return first / _safe_denominator(second)
    second = pl.col(feature.columns[1])
    return first * second
