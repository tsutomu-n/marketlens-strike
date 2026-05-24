from __future__ import annotations

from datetime import datetime
from pathlib import Path

import polars as pl
from pydantic import BaseModel

from sis.paper.fills import PaperFill


class PaperPosition(BaseModel):
    venue: str
    canonical_symbol: str
    side: str
    quantity: float
    avg_entry_price: float
    opened_at: datetime
    updated_at: datetime
    realized_pnl: float = 0.0


class PaperPortfolio:
    def __init__(self, positions: list[PaperPosition] | None = None) -> None:
        self._positions: dict[tuple[str, str, str], PaperPosition] = {}
        for position in positions or []:
            key = (position.venue, position.canonical_symbol, position.side)
            self._positions[key] = position

    def positions(self) -> list[PaperPosition]:
        return list(self._positions.values())

    def apply_fill(self, fill: PaperFill) -> float:
        key = (fill.venue, fill.canonical_symbol, fill.side)
        position = self._positions.get(key)
        if fill.action.startswith("enter_"):
            if position is None:
                self._positions[key] = PaperPosition(
                    venue=fill.venue,
                    canonical_symbol=fill.canonical_symbol,
                    side=fill.side,
                    quantity=fill.quantity,
                    avg_entry_price=fill.price,
                    opened_at=fill.ts_fill,
                    updated_at=fill.ts_fill,
                )
            else:
                total_quantity = position.quantity + fill.quantity
                position.avg_entry_price = (
                    (position.avg_entry_price * position.quantity) + (fill.price * fill.quantity)
                ) / total_quantity
                position.quantity = total_quantity
                position.updated_at = fill.ts_fill
            return 0.0

        if position is None:
            return 0.0

        closing_quantity = min(position.quantity, fill.quantity)
        if fill.side == "long":
            realized = (fill.price - position.avg_entry_price) * closing_quantity
        else:
            realized = (position.avg_entry_price - fill.price) * closing_quantity
        position.quantity -= closing_quantity
        position.realized_pnl += realized
        position.updated_at = fill.ts_fill
        if position.quantity <= 0:
            del self._positions[key]
        return realized


def positions_to_frame(positions: list[PaperPosition]) -> pl.DataFrame:
    if not positions:
        return pl.DataFrame(
            schema={
                "venue": pl.Utf8,
                "canonical_symbol": pl.Utf8,
                "side": pl.Utf8,
                "quantity": pl.Float64,
                "avg_entry_price": pl.Float64,
                "opened_at": pl.Datetime(time_zone="UTC"),
                "updated_at": pl.Datetime(time_zone="UTC"),
                "realized_pnl": pl.Float64,
            }
        )
    return pl.from_dicts([position.model_dump(mode="json") for position in positions])


def write_positions_parquet(path: Path, positions: list[PaperPosition]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    positions_to_frame(positions).write_parquet(path)
    return path
