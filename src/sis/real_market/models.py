from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RealMarketBar(BaseModel):
    ts_start: datetime
    ts_end: datetime
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    source: str
    delay_seconds: float | None = None
    raw_payload_ref: str | None = None


class RealMarketFeature(BaseModel):
    ts: datetime
    symbol: str
    timeframe: str
    close: float
    return_5m: float | None = None
    return_15m: float | None = None
    realized_vol_15m: float | None = None
    volume_zscore_15m: float | None = None
    source_confidence: float = 0.0
    market_session: str = "unknown"
    event_flags: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
