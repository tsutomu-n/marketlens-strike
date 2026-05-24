from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import polars as pl
from pydantic import BaseModel, Field


class PaperOrder(BaseModel):
    order_id: str = Field(default_factory=lambda: uuid4().hex)
    ts_order: datetime
    venue: str
    canonical_symbol: str
    side: str
    action: str
    quantity: float
    strategy_name: str | None = None
    notes: list[str] = Field(default_factory=list)


def orders_to_frame(orders: list[PaperOrder]) -> pl.DataFrame:
    if not orders:
        return pl.DataFrame(
            schema={
                "order_id": pl.Utf8,
                "ts_order": pl.Datetime(time_zone="UTC"),
                "venue": pl.Utf8,
                "canonical_symbol": pl.Utf8,
                "side": pl.Utf8,
                "action": pl.Utf8,
                "quantity": pl.Float64,
                "strategy_name": pl.Utf8,
            }
        )
    return pl.from_dicts([order.model_dump(mode="json") for order in orders])


def write_orders_parquet(path: Path, orders: list[PaperOrder]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    orders_to_frame(orders).write_parquet(path)
    return path
