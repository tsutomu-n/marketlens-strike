from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.run_profile import DEFAULT_FORBIDDEN_CLAIMS, LEGACY_FORBIDDEN_CLAIMS
from sis.venues.ids import VenueId

PROXY_REQUIREMENTS = {
    "XYZ100": {"QQQ"},
    "SP500": {"SPY"},
}
ALLOWED_EXIT_PRIORITY_ITEMS = {
    "break_even_stop",
    "stop_loss",
    "partial_take_profit",
    "take_profit",
    "trailing_stop",
    "time_stop",
}
DEFAULT_EXIT_PRIORITY = (
    "break_even_stop,stop_loss,partial_take_profit,take_profit,trailing_stop,time_stop"
)


class SymbolBinding(BaseModel):
    execution_venue: VenueId
    execution_symbol: str
    real_market_symbol: str
    asset_class: str
    country: str | None = None
    currency: str = "USD"

    @model_validator(mode="after")
    def validate_proxy_binding(self) -> SymbolBinding:
        execution_symbol = self.execution_symbol.strip().upper()
        real_market_symbol = self.real_market_symbol.strip().upper()
        if not execution_symbol:
            raise ValueError("execution_symbol must be non-empty")
        if not real_market_symbol:
            raise ValueError("real_market_symbol must be non-empty")
        expected = (
            PROXY_REQUIREMENTS.get(execution_symbol)
            if self.execution_venue == "trade_xyz"
            else None
        )
        if expected is not None and real_market_symbol not in expected:
            raise ValueError(
                f"{execution_symbol} requires real_market_symbol in {sorted(expected)}"
            )
        self.execution_symbol = execution_symbol
        self.real_market_symbol = real_market_symbol
        return self


class StrategyExperimentSpec(BaseModel):
    schema_version: Literal["strategy_experiment_spec.v1"]
    strategy_id: str
    strategy_family: str
    strategy_version: str
    enabled: bool
    description: str | None
    symbol_bindings: list[SymbolBinding]
    generator_id: str
    parameter_grid: dict[str, list[Any]]
    evaluation_plan_id: str
    run_profile_id: str
    forbidden_claims: list[str] = Field(default_factory=lambda: DEFAULT_FORBIDDEN_CLAIMS[:])

    @model_validator(mode="after")
    def validate_strategy_lab_guards(self) -> StrategyExperimentSpec:
        if not self.symbol_bindings:
            raise ValueError("symbol_bindings must include at least one binding")
        for name in ("strategy_id", "strategy_family", "strategy_version", "generator_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        legacy = set(LEGACY_FORBIDDEN_CLAIMS).intersection(self.forbidden_claims)
        if legacy:
            raise ValueError(
                "forbidden_claims uses legacy claim names; "
                f"use *_claimed names instead: {sorted(legacy)}"
            )
        missing = set(DEFAULT_FORBIDDEN_CLAIMS).difference(self.forbidden_claims)
        if missing:
            raise ValueError(f"forbidden_claims missing: {sorted(missing)}")
        return self


class StrategySignalRecord(BaseModel):
    schema_version: Literal["strategy_signal.v1"]
    signal_id: str
    generated_at: datetime
    strategy_id: str
    strategy_family: str
    strategy_version: str
    trial_id: str | None
    parameter_hash: str | None
    ts_signal: datetime
    timeframe: str
    execution_venue: VenueId
    execution_symbol: str
    real_market_symbol: str
    multi_leg_group_id: str | None = None
    multi_leg_leg_index: int | None = None
    multi_leg_leg_count: int | None = None
    multi_leg_anchor_real_market_symbol: str | None = None
    side: Literal["long", "short", "close", "reduce", "add", "rebalance", "none"]
    raw_score: float | None
    rank_score: float | None
    percentile_rank: float | None
    tail_bucket: Literal["top", "middle", "bottom", "none"]
    confidence: float
    source_confidence: float | None
    venue_quality_score: float | None
    feature_snapshot_ref: str | None
    quote_ref: str | None
    tracking_ref: str | None
    stop_loss_bps: float | None = None
    min_stop_loss_bps: float | None = None
    max_stop_loss_bps: float | None = None
    take_profit_bps: float | None = None
    min_take_profit_bps: float | None = None
    max_take_profit_bps: float | None = None
    min_reward_risk_ratio: float | None = None
    reward_risk_ratio: float | None = None
    trailing_stop_bps: float | None = None
    trailing_stop_activation_bps: float | None = None
    partial_take_profit_bps: float | None = None
    partial_exit_fraction: float | None = None
    min_holding_minutes: int | None = None
    max_holding_minutes: int | None = None
    exit_priority: str = DEFAULT_EXIT_PRIORITY
    exit_on_opposite_signal: bool = False
    exit_on_close_signal: bool = False
    exit_on_reduce_signal: bool = False
    reduce_fraction: float | None = None
    exit_on_add_signal: bool = False
    add_fraction: float | None = None
    exit_on_rebalance_signal: bool = False
    rebalance_target_fraction: float | None = None
    rebalance_min_delta_fraction: float | None = None
    bracket_type: Literal["none", "oco"] = "none"
    bracket_time_stop_minutes: int | None = None
    bracket_break_even_after_bps: float | None = None
    bracket_break_even_after_partial_take_profit: bool = False
    entry_order_type: Literal["market", "limit", "stop_market"] = "market"
    entry_limit_offset_bps: float | None = None
    entry_stop_offset_bps: float | None = None
    entry_timeout_minutes: int | None = None
    entry_time_in_force: Literal["gtc", "gtd", "ioc", "fok"] = "gtc"
    entry_post_only: bool = False
    entry_reduce_only: bool = False
    slippage_bps: float = 0.0
    max_fill_fraction: float = 1.0
    min_fill_fraction: float | None = None
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
    max_capacity_usage_ratio: float | None = None
    capacity_usage_ratio: float | None = None
    max_correlation_crowding_score: float | None = None
    correlation_crowding_score: float | None = None
    min_fee_edge_bps: float | None = None
    fee_edge_bps: float | None = None
    position_weight: float | None = None
    notional_usd: float | None = None
    reason_codes: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_signal_record(self) -> StrategySignalRecord:
        if not self.execution_symbol.strip():
            raise ValueError("execution_symbol must be non-empty")
        if not self.real_market_symbol.strip():
            raise ValueError("real_market_symbol must be non-empty")
        if self.multi_leg_group_id is not None and not self.multi_leg_group_id.strip():
            raise ValueError("multi_leg_group_id must be non-empty when set")
        if self.multi_leg_anchor_real_market_symbol is not None:
            if not self.multi_leg_anchor_real_market_symbol.strip():
                raise ValueError("multi_leg_anchor_real_market_symbol must be non-empty when set")
            self.multi_leg_anchor_real_market_symbol = (
                self.multi_leg_anchor_real_market_symbol.strip().upper()
            )
        if self.multi_leg_leg_index is not None and self.multi_leg_leg_index <= 0:
            raise ValueError("multi_leg_leg_index must be positive")
        if self.multi_leg_leg_count is not None and self.multi_leg_leg_count <= 0:
            raise ValueError("multi_leg_leg_count must be positive")
        if (
            self.multi_leg_leg_index is not None
            and self.multi_leg_leg_count is not None
            and self.multi_leg_leg_index > self.multi_leg_leg_count
        ):
            raise ValueError("multi_leg_leg_index must be <= multi_leg_leg_count")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.rank_score is not None and not 0.0 <= self.rank_score <= 1.0:
            raise ValueError("rank_score must be between 0 and 1")
        if self.percentile_rank is not None and not 0.0 <= self.percentile_rank <= 1.0:
            raise ValueError("percentile_rank must be between 0 and 1")
        if self.stop_loss_bps is not None and self.stop_loss_bps < 0:
            raise ValueError("stop_loss_bps must be >= 0")
        if self.min_stop_loss_bps is not None and self.min_stop_loss_bps < 0:
            raise ValueError("min_stop_loss_bps must be >= 0")
        if self.max_stop_loss_bps is not None and self.max_stop_loss_bps < 0:
            raise ValueError("max_stop_loss_bps must be >= 0")
        if (
            self.min_stop_loss_bps is not None
            and self.max_stop_loss_bps is not None
            and self.max_stop_loss_bps < self.min_stop_loss_bps
        ):
            raise ValueError("max_stop_loss_bps must be >= min_stop_loss_bps")
        if self.take_profit_bps is not None and self.take_profit_bps < 0:
            raise ValueError("take_profit_bps must be >= 0")
        if self.min_take_profit_bps is not None and self.min_take_profit_bps < 0:
            raise ValueError("min_take_profit_bps must be >= 0")
        if self.max_take_profit_bps is not None and self.max_take_profit_bps < 0:
            raise ValueError("max_take_profit_bps must be >= 0")
        if (
            self.min_take_profit_bps is not None
            and self.max_take_profit_bps is not None
            and self.max_take_profit_bps < self.min_take_profit_bps
        ):
            raise ValueError("max_take_profit_bps must be >= min_take_profit_bps")
        if self.min_reward_risk_ratio is not None and self.min_reward_risk_ratio < 0:
            raise ValueError("min_reward_risk_ratio must be >= 0")
        if self.reward_risk_ratio is not None and self.reward_risk_ratio < 0:
            raise ValueError("reward_risk_ratio must be >= 0")
        if self.trailing_stop_bps is not None and self.trailing_stop_bps < 0:
            raise ValueError("trailing_stop_bps must be >= 0")
        if self.trailing_stop_activation_bps is not None and self.trailing_stop_activation_bps < 0:
            raise ValueError("trailing_stop_activation_bps must be >= 0")
        if self.partial_take_profit_bps is not None and self.partial_take_profit_bps < 0:
            raise ValueError("partial_take_profit_bps must be >= 0")
        if self.partial_exit_fraction is not None and not 0.0 <= self.partial_exit_fraction <= 1.0:
            raise ValueError("partial_exit_fraction must be between 0 and 1")
        if self.min_holding_minutes is not None and self.min_holding_minutes <= 0:
            raise ValueError("min_holding_minutes must be positive")
        if self.max_holding_minutes is not None and self.max_holding_minutes <= 0:
            raise ValueError("max_holding_minutes must be positive")
        if (
            self.min_holding_minutes is not None
            and self.max_holding_minutes is not None
            and self.max_holding_minutes < self.min_holding_minutes
        ):
            raise ValueError("max_holding_minutes must be >= min_holding_minutes")
        if not self.exit_priority.strip():
            raise ValueError("exit_priority must be non-empty")
        exit_priority_items = [
            item.strip() for item in self.exit_priority.split(",") if item.strip()
        ]
        if len(set(exit_priority_items)) != len(exit_priority_items):
            raise ValueError("exit_priority must not contain duplicates")
        unsupported_exit_priority = [
            item for item in exit_priority_items if item not in ALLOWED_EXIT_PRIORITY_ITEMS
        ]
        if unsupported_exit_priority:
            raise ValueError(f"Unsupported exit_priority item: {unsupported_exit_priority}")
        if self.reduce_fraction is not None and not 0.0 <= self.reduce_fraction <= 1.0:
            raise ValueError("reduce_fraction must be between 0 and 1")
        if self.add_fraction is not None and not 0.0 <= self.add_fraction <= 1.0:
            raise ValueError("add_fraction must be between 0 and 1")
        if self.rebalance_target_fraction is not None and self.rebalance_target_fraction < 0:
            raise ValueError("rebalance_target_fraction must be >= 0")
        if self.rebalance_min_delta_fraction is not None and self.rebalance_min_delta_fraction < 0:
            raise ValueError("rebalance_min_delta_fraction must be >= 0")
        if self.bracket_time_stop_minutes is not None and self.bracket_time_stop_minutes < 0:
            raise ValueError("bracket_time_stop_minutes must be >= 0")
        if self.bracket_break_even_after_bps is not None and self.bracket_break_even_after_bps < 0:
            raise ValueError("bracket_break_even_after_bps must be >= 0")
        if self.entry_limit_offset_bps is not None and self.entry_limit_offset_bps < 0:
            raise ValueError("entry_limit_offset_bps must be >= 0")
        if self.entry_stop_offset_bps is not None and self.entry_stop_offset_bps < 0:
            raise ValueError("entry_stop_offset_bps must be >= 0")
        if self.entry_timeout_minutes is not None and self.entry_timeout_minutes < 0:
            raise ValueError("entry_timeout_minutes must be >= 0")
        if self.entry_time_in_force == "gtd" and self.entry_timeout_minutes is None:
            raise ValueError("entry_timeout_minutes is required when entry_time_in_force is gtd")
        if self.entry_time_in_force in {"ioc", "fok"} and self.entry_timeout_minutes is not None:
            raise ValueError("entry_timeout_minutes cannot be set for ioc or fok")
        if self.entry_post_only and self.entry_order_type != "limit":
            raise ValueError("entry_post_only is only supported for limit entry")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must be >= 0")
        if not 0.0 <= self.max_fill_fraction <= 1.0:
            raise ValueError("max_fill_fraction must be between 0 and 1")
        if self.min_fill_fraction is not None and not 0.0 <= self.min_fill_fraction <= 1.0:
            raise ValueError("min_fill_fraction must be between 0 and 1")
        if self.max_spread_bps is not None and self.max_spread_bps < 0:
            raise ValueError("max_spread_bps must be >= 0")
        if self.min_depth_usd is not None and self.min_depth_usd < 0:
            raise ValueError("min_depth_usd must be >= 0")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ValueError("max_latency_ms must be >= 0")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")
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
        if self.max_borrow_cost_bps is not None and self.max_borrow_cost_bps < 0:
            raise ValueError("max_borrow_cost_bps must be >= 0")
        if self.borrow_cost_bps is not None and self.borrow_cost_bps < 0:
            raise ValueError("borrow_cost_bps must be >= 0")
        if self.max_tax_drag_bps is not None and self.max_tax_drag_bps < 0:
            raise ValueError("max_tax_drag_bps must be >= 0")
        if self.tax_drag_bps is not None and self.tax_drag_bps < 0:
            raise ValueError("tax_drag_bps must be >= 0")
        if self.max_turnover_pressure is not None and self.max_turnover_pressure < 0:
            raise ValueError("max_turnover_pressure must be >= 0")
        if self.turnover_pressure is not None and self.turnover_pressure < 0:
            raise ValueError("turnover_pressure must be >= 0")
        if self.max_capacity_usage_ratio is not None and self.max_capacity_usage_ratio < 0:
            raise ValueError("max_capacity_usage_ratio must be >= 0")
        if self.capacity_usage_ratio is not None and self.capacity_usage_ratio < 0:
            raise ValueError("capacity_usage_ratio must be >= 0")
        if (
            self.max_correlation_crowding_score is not None
            and self.max_correlation_crowding_score < 0
        ):
            raise ValueError("max_correlation_crowding_score must be >= 0")
        if self.correlation_crowding_score is not None and self.correlation_crowding_score < 0:
            raise ValueError("correlation_crowding_score must be >= 0")
        if self.depth_column is not None and not self.depth_column.strip():
            raise ValueError("depth_column must be non-empty when set")
        if not 0.0 <= self.depth_participation_rate <= 1.0:
            raise ValueError("depth_participation_rate must be between 0 and 1")
        if self.position_weight is not None and self.position_weight < 0:
            raise ValueError("position_weight must be >= 0")
        if self.notional_usd is not None and self.notional_usd < 0:
            raise ValueError("notional_usd must be >= 0")
        self.execution_symbol = self.execution_symbol.strip().upper()
        self.real_market_symbol = self.real_market_symbol.strip().upper()
        return self
