from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.research.strategy_lab.authoring.contracts import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.validation import _resolve_path


def _apply_confirmation_panels(
    frame: pl.DataFrame, spec: StrategyAuthoringSpec, *, data_dir: Path
) -> pl.DataFrame:
    if not spec.data.confirmation_panels:
        return frame
    enriched = frame.sort(["canonical_symbol", "ts"])
    for panel in spec.data.confirmation_panels:
        panel_path = _resolve_path(panel.path, data_dir)
        raw_panel = pl.read_parquet(panel_path)
        if raw_panel.is_empty():
            continue
        stamp_column = f"__{panel.prefix}_ts"
        rename_map = {
            column: f"{panel.prefix}_{column}"
            for column in raw_panel.columns
            if column not in {"ts", "canonical_symbol"}
        }
        right = (
            raw_panel.with_columns(pl.col("ts").alias(stamp_column))
            .rename(rename_map)
            .sort(["canonical_symbol", "ts"])
        )
        joined = enriched.join_asof(
            right,
            on="ts",
            by="canonical_symbol",
            strategy="backward",
            check_sortedness=False,
        )
        prefixed_columns = list(rename_map.values())
        if panel.max_age_minutes is not None and prefixed_columns:
            age_minutes = (pl.col("ts") - pl.col(stamp_column)).dt.total_minutes()
            joined = joined.with_columns(
                [
                    pl.when(age_minutes <= panel.max_age_minutes)
                    .then(pl.col(column))
                    .otherwise(None)
                    .alias(column)
                    for column in prefixed_columns
                ]
            )
        enriched = joined.drop(stamp_column) if stamp_column in joined.columns else joined
    return enriched
