from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import polars as pl
from pydantic import BaseModel, Field


class PaperFill(BaseModel):
    fill_id: str = Field(default_factory=lambda: uuid4().hex)
    ts_fill: datetime
    venue: str
    canonical_symbol: str
    side: str
    action: str
    quantity: float
    price: float
    strategy_name: str | None = None
    source_confidence: float | None = None
    venue_quality_score: float | None = None
    block_reasons: list[str] = Field(default_factory=list)
    fee_mode: str | None = None
    estimated_round_trip_cost_bps: float | None = None
    fill_price_source: str | None = None
    notes: list[str] = Field(default_factory=list)


def fills_to_frame(fills: list[PaperFill]) -> pl.DataFrame:
    if not fills:
        return pl.DataFrame(
            schema={
                "fill_id": pl.Utf8,
                "ts_fill": pl.Datetime(time_zone="UTC"),
                "venue": pl.Utf8,
                "canonical_symbol": pl.Utf8,
                "side": pl.Utf8,
                "action": pl.Utf8,
                "quantity": pl.Float64,
                "price": pl.Float64,
                "strategy_name": pl.Utf8,
                "source_confidence": pl.Float64,
                "venue_quality_score": pl.Float64,
                "block_reasons": pl.List(pl.Utf8),
                "fee_mode": pl.Utf8,
                "estimated_round_trip_cost_bps": pl.Float64,
                "fill_price_source": pl.Utf8,
            }
        )
    return pl.from_dicts(
        [fill.model_dump(mode="json") for fill in fills],
        infer_schema_length=None,
    )


def write_fills_parquet(path: Path, fills: list[PaperFill]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fills_to_frame(fills).write_parquet(path)
    return path
