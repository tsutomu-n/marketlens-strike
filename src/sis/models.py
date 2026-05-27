from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Venue(str, Enum):
    TRADE_XYZ = "trade_xyz"
    LIGHTER = "lighter"
    BITMEX_READONLY = "bitmex_readonly"
    LEGACY_GTRADE = "legacy_gtrade"
    LEGACY_OSTIUM = "legacy_ostium"
    # Backward compatibility aliases for legacy-runtime surfaces.
    GTRADE = "gtrade"
    OSTIUM = "ostium"


class AssetClass(str, Enum):
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    BASKET_INDEX = "basket_index"
    CRYPTO_BETA_EQUITY = "crypto_beta_equity"
    # Backward compatibility alias used by archived flows.
    COMMODITY = "commodity"
    UNKNOWN = "unknown"


class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CLOSE_ONLY = "close_only"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class SessionType(str, Enum):
    REGULAR = "regular"
    PREMARKET = "premarket"
    AFTERHOURS = "afterhours"
    INTERNAL = "internal"
    CLOSED = "closed"
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

    dex: str | None = None
    coin: str | None = None
    asset_id: int | None = None
    perp_dex_index: int | None = None
    index_in_meta: int | None = None
    real_market_symbol: str | None = None
    country: str | None = None
    currency: str | None = None
    fee_mode: str | None = None
    taker_fee_bps: float | None = None
    maker_fee_bps: float | None = None
    discovery_bound_bps: float | None = None
    oi_cap_usd: float | None = None
    external_session: str | None = None
    internal_session: str | None = None

    # Legacy fields kept for archive compatibility.
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
    session_type: SessionType = SessionType.UNKNOWN
    is_tradable: bool = False
    session_source: str
    notes: list[str] = Field(default_factory=list)


class QuoteLog(BaseModel):
    ts_client: datetime
    venue: Venue
    canonical_symbol: str
    venue_symbol: str
    source: str
    raw_payload_sha256: str

    recv_ts_ms: int | None = None
    source_ts_ms: int | None = None
    dex: str | None = None
    coin: str | None = None
    asset_id: int | None = None
    real_market_symbol: str | None = None

    pair_index: int | None = None
    pair_id: int | None = None
    chain: str | None = None
    mark_price: float | None = None
    index_price: float | None = None
    oracle_price: float | None = None
    best_bid: float | None = None
    best_ask: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    mid_price: float | None = None
    exec_buy_price: float | None = None
    exec_sell_price: float | None = None
    spread_bps: float | None = None
    depth_10bps_usd: float | None = None
    depth_25bps_usd: float | None = None
    bid_depth_10bps_usd: float | None = None
    ask_depth_10bps_usd: float | None = None
    bid_depth_25bps_usd: float | None = None
    ask_depth_25bps_usd: float | None = None
    min_side_depth_10bps_usd: float | None = None
    funding_rate: float | None = None
    funding_interval_minutes: int | None = None
    open_interest_usd: float | None = None
    premium: float | None = None
    prev_day_price: float | None = None
    day_notional_volume: float | None = None
    fee_mode: str | None = None
    oracle_ts_ms: int | None = None

    market_status: MarketStatus = MarketStatus.UNKNOWN
    session_type: SessionType = SessionType.UNKNOWN
    is_tradable: bool = False
    source_confidence: float | None = None
    venue_quality_score: float | None = None
    block_reasons: list[str] = Field(default_factory=list)

    raw_payload_ref: str | None = None
    raw_payload: dict[str, Any] | None = None


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
