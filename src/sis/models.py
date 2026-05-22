from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Venue(str, Enum):
    GTRADE = "gtrade"
    OSTIUM = "ostium"


class AssetClass(str, Enum):
    INDEX = "index"
    COMMODITY = "commodity"
    UNKNOWN = "unknown"


class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CLOSE_ONLY = "close_only"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class Decision(str, Enum):
    GO = "GO"
    CONDITIONAL_GO = "CONDITIONAL_GO"
    CONDITIONAL_GO_DATA_READY = "CONDITIONAL_GO_DATA_READY"
    CONDITIONAL_GO_NEEDS_LIVE_WINDOW = "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST = "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST"
    NO_GO = "NO_GO"
    NO_GO_COST = "NO_GO_COST"
    NO_GO_STALE = "NO_GO_STALE"
    NO_GO_SESSION = "NO_GO_SESSION"


class InstrumentSpec(BaseModel):
    venue: Venue
    canonical_symbol: str
    venue_symbol: str
    asset_class: AssetClass
    pair_index: int | None = None
    pair_id: int | None = None
    chain: str | list[str] | None = None
    collateral: str | list[str] | None = None
    api_readable: bool = True
    api_orderable: bool = False
    execution_price_ref: str | None = None
    liquidation_price_ref: str | None = None
    opening_fee_bps: float | None = None
    rollover_fee_per_block: str | None = None
    rollover_rate_long: str | None = None
    rollover_rate_short: str | None = None
    open_interest: str | None = None
    buy_open_interest: str | None = None
    sell_open_interest: str | None = None
    max_open_interest: str | None = None
    max_leverage: float | None = None
    overnight_max_leverage: float | None = None
    trading_hours_ref: str | None = None
    is_day_trading_closed: bool | None = None
    seconds_to_toggle_is_day_trading_closed: int | None = None
    active: bool = True
    notes: list[str] = Field(default_factory=list)


class MarketSession(BaseModel):
    venue: Venue
    canonical_symbol: str
    market_status: MarketStatus = MarketStatus.UNKNOWN
    is_tradable: bool = False
    session_source: str
    notes: list[str] = Field(default_factory=list)


class QuoteLog(BaseModel):
    ts_client: datetime
    venue: Venue
    canonical_symbol: str
    venue_symbol: str
    pair_index: int | None = None
    pair_id: int | None = None
    chain: str | None = None
    mark_price: float | None = None
    index_price: float | None = None
    oracle_price: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    mid_price: float | None = None
    exec_buy_price: float | None = None
    exec_sell_price: float | None = None
    spread_bps: float | None = None
    oracle_ts_ms: int | None = None
    market_status: MarketStatus = MarketStatus.UNKNOWN
    is_tradable: bool = False
    source: str
    raw_payload_sha256: str
    raw_payload_ref: str | None = None
    raw_payload: dict | None = None


class CostSnapshot(BaseModel):
    venue: Venue
    canonical_symbol: str
    open_fee_bps: float | None = None
    close_fee_bps: float | None = None
    fixed_spread_bps: float | None = None
    spread_p50_bps: float | None = None
    spread_p90_bps: float | None = None
    spread_p99_bps: float | None = None
    holding_cost_4h_bps: float | None = None
    holding_cost_24h_bps: float | None = None
    holding_cost_72h_bps: float | None = None
    stale_rate: float | None = None
    tradable_rate: float | None = None
    notes: list[str] = Field(default_factory=list)


class GoNoGoCriterion(BaseModel):
    criterion: str
    result: str
    evidence: str | None = None


class VenueDecision(BaseModel):
    venue: str
    decision: Decision
    main_blocker: str | None = None


class GoNoGoReport(BaseModel):
    decision: Decision
    summary: str = ""
    criteria: list[GoNoGoCriterion]
    venue_decisions: list[VenueDecision] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
