from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature


TIMESTAMP_DERIVED_OPS = {
    "ts_weekday",
    "ts_hour",
    "ts_month",
    "ts_day",
}


def timestamp_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "ts_weekday":
        return first.dt.weekday() - 1
    if feature.op == "ts_hour":
        return first.dt.hour()
    if feature.op == "ts_month":
        return first.dt.month()
    return first.dt.day()
