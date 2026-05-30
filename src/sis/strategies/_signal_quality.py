from __future__ import annotations

from typing import Any

import polars as pl

QUALITY_COLUMN_SCHEMA: dict[str, Any] = {
    "source_confidence": pl.Float64,
    "venue_quality_score": pl.Float64,
}


def quality_column_expressions(feature_frame: pl.DataFrame) -> list[pl.Expr]:
    return [
        (
            pl.col(column_name).cast(dtype)
            if column_name in feature_frame.columns
            else pl.lit(None, dtype=dtype).alias(column_name)
        )
        for column_name, dtype in QUALITY_COLUMN_SCHEMA.items()
    ]
