from __future__ import annotations

from datetime import datetime

import polars as pl
from pydantic import BaseModel, Field, model_validator


class BlockedEvent(BaseModel):
    event_ts: datetime
    symbol: str
    action: str
    reason: str
    reason_detail: str = ""
    strategy_id: str
    signal_id: str | None = None
    row_index: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_blocked_event(self) -> BlockedEvent:
        self.symbol = self.symbol.strip().upper()
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if not self.action.strip():
            raise ValueError("action must be non-empty")
        if not self.reason.strip():
            raise ValueError("reason must be non-empty")
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must be non-empty")
        return self


def blocked_events_to_frame(events: list[BlockedEvent]) -> pl.DataFrame:
    schema = {
        "event_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "action": pl.Utf8,
        "reason": pl.Utf8,
        "reason_detail": pl.Utf8,
        "strategy_id": pl.Utf8,
        "signal_id": pl.Utf8,
        "row_index": pl.Int64,
    }
    if not events:
        return pl.DataFrame(schema=schema)
    rows = [event.model_dump(mode="python") for event in events]
    return pl.from_dicts(
        rows,
        schema=schema,
        infer_schema_length=None,
    )
