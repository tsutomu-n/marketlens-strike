from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TrackingRecord(BaseModel):
    ts_client: datetime
    canonical_symbol: str
    venue: str
    real_market_symbol: str
    real_price: float | None = None
    real_return_5m: float | None = None
    real_return_15m: float | None = None
    real_volume: float | None = None
    real_volume_zscore_15m: float | None = None
    realized_vol_15m: float | None = None
    venue_mark: float | None = None
    venue_oracle: float | None = None
    venue_mid: float | None = None
    venue_best_bid: float | None = None
    venue_best_ask: float | None = None
    venue_spread_bps: float | None = None
    venue_depth_10bps_usd: float | None = None
    funding_rate: float | None = None
    mark_real_diff_bps: float | None = None
    oracle_real_diff_bps: float | None = None
    source_confidence: float = 0.0
    venue_quality_score: float = 0.0
    trade_allowed: bool = False
    block_reasons: list[str] = Field(default_factory=list)
