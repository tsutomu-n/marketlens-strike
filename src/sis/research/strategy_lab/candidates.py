from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TradeCandidate(BaseModel):
    schema_version: Literal["trade_candidate.v1"]
    candidate_id: str
    generated_at: datetime
    signal_id: str | None
    strategy_id: str
    trial_id: str | None
    execution_venue: Literal["trade_xyz"]
    execution_symbol: str
    real_market_symbol: str
    side: Literal["long", "short", "none"]
    timeframe: str
    status: Literal["candidate", "blocked", "no_signal", "hold"]
    raw_score: float | None
    rank_score: float | None
    percentile_rank: float | None
    tail_bucket: Literal["top", "middle", "bottom", "none"]
    confidence: float
    unique_contribution_score: float | None = None
    index_exposure_score: float | None = None
    entry_reason_codes: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    stop_loss_bps: float | None = None
    take_profit_bps: float | None = None
    trailing_stop_bps: float | None = None
    partial_take_profit_bps: float | None = None
    partial_exit_fraction: float | None = None
    min_holding_minutes: int | None = None
    exit_on_opposite_signal: bool = False
    bracket_type: Literal["none", "oco"] = "none"
    bracket_time_stop_minutes: int | None = None
    bracket_break_even_after_bps: float | None = None
    entry_order_type: Literal["market", "limit", "stop_market"] = "market"
    entry_limit_offset_bps: float | None = None
    entry_stop_offset_bps: float | None = None
    entry_timeout_minutes: int | None = None
    entry_time_in_force: Literal["gtc", "gtd", "ioc", "fok"] = "gtc"
    entry_post_only: bool = False
    slippage_bps: float = 0.0
    max_fill_fraction: float = 1.0
    max_spread_bps: float | None = None
    min_depth_usd: float | None = None
    depth_column: str | None = None
    depth_participation_rate: float = 1.0
    max_latency_ms: float | None = None
    latency_ms: float | None = None
    min_queue_position_score: float | None = None
    queue_position_score: float | None = None
    min_borrow_availability_ratio: float | None = None
    borrow_availability_ratio: float | None = None
    max_borrow_cost_bps: float | None = None
    borrow_cost_bps: float | None = None
    max_tax_drag_bps: float | None = None
    tax_drag_bps: float | None = None
    max_turnover_pressure: float | None = None
    turnover_pressure: float | None = None
    min_fee_edge_bps: float | None = None
    fee_edge_bps: float | None = None
    position_weight: float | None = None
    notional_usd: float | None = None
    feature_snapshot_ref: str | None
    quote_ref: str | None
    tracking_ref: str | None
    live_order_submitted: bool = False

    @model_validator(mode="after")
    def validate_candidate(self) -> TradeCandidate:
        for field_name in ("candidate_id", "strategy_id", "execution_symbol", "real_market_symbol"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.live_order_submitted:
            raise ValueError("live_order_submitted must remain false for TradeCandidate")
        if self.rank_score is not None and not 0.0 <= self.rank_score <= 1.0:
            raise ValueError("rank_score must be between 0 and 1")
        if self.percentile_rank is not None and not 0.0 <= self.percentile_rank <= 1.0:
            raise ValueError("percentile_rank must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.partial_exit_fraction is not None and not 0.0 <= self.partial_exit_fraction <= 1.0:
            raise ValueError("partial_exit_fraction must be between 0 and 1")
        if self.min_holding_minutes is not None and self.min_holding_minutes <= 0:
            raise ValueError("min_holding_minutes must be positive")
        for field_name in (
            "stop_loss_bps",
            "take_profit_bps",
            "trailing_stop_bps",
            "partial_take_profit_bps",
            "entry_limit_offset_bps",
            "entry_stop_offset_bps",
            "bracket_break_even_after_bps",
            "slippage_bps",
            "max_spread_bps",
            "min_depth_usd",
            "max_latency_ms",
            "latency_ms",
            "max_borrow_cost_bps",
            "borrow_cost_bps",
            "max_tax_drag_bps",
            "tax_drag_bps",
            "max_turnover_pressure",
            "turnover_pressure",
            "position_weight",
            "notional_usd",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be >= 0")
        if self.entry_timeout_minutes is not None and self.entry_timeout_minutes < 0:
            raise ValueError("entry_timeout_minutes must be >= 0")
        if self.bracket_time_stop_minutes is not None and self.bracket_time_stop_minutes < 0:
            raise ValueError("bracket_time_stop_minutes must be >= 0")
        if not 0.0 <= self.max_fill_fraction <= 1.0:
            raise ValueError("max_fill_fraction must be between 0 and 1")
        if self.depth_column is not None and not self.depth_column.strip():
            raise ValueError("depth_column must be non-empty when set")
        if not 0.0 <= self.depth_participation_rate <= 1.0:
            raise ValueError("depth_participation_rate must be between 0 and 1")
        if (
            self.min_queue_position_score is not None
            and not 0.0 <= self.min_queue_position_score <= 1.0
        ):
            raise ValueError("min_queue_position_score must be between 0 and 1")
        if self.queue_position_score is not None and not 0.0 <= self.queue_position_score <= 1.0:
            raise ValueError("queue_position_score must be between 0 and 1")
        if (
            self.min_borrow_availability_ratio is not None
            and not 0.0 <= self.min_borrow_availability_ratio <= 1.0
        ):
            raise ValueError("min_borrow_availability_ratio must be between 0 and 1")
        if (
            self.borrow_availability_ratio is not None
            and not 0.0 <= self.borrow_availability_ratio <= 1.0
        ):
            raise ValueError("borrow_availability_ratio must be between 0 and 1")
        self.execution_symbol = self.execution_symbol.strip().upper()
        self.real_market_symbol = self.real_market_symbol.strip().upper()
        return self
