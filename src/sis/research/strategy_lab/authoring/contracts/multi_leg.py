from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.authoring.contracts.core import EntryRules


class MultiLegEntry(BaseModel):
    real_market_symbol: str
    side: Literal["long", "short", "same", "opposite"]
    position_weight: float = 1.0
    position_weight_column: str | None = None
    notional_usd: float | None = None
    notional_usd_column: str | None = None
    stop_loss_bps: float | None = None
    stop_loss_bps_column: str | None = None
    min_stop_loss_bps: float | None = None
    min_stop_loss_bps_column: str | None = None
    max_stop_loss_bps: float | None = None
    max_stop_loss_bps_column: str | None = None
    take_profit_bps: float | None = None
    take_profit_bps_column: str | None = None
    min_take_profit_bps: float | None = None
    min_take_profit_bps_column: str | None = None
    max_take_profit_bps: float | None = None
    max_take_profit_bps_column: str | None = None
    trailing_stop_bps: float | None = None
    trailing_stop_bps_column: str | None = None
    trailing_stop_activation_bps: float | None = None
    trailing_stop_activation_bps_column: str | None = None
    partial_take_profit_bps: float | None = None
    partial_take_profit_bps_column: str | None = None
    partial_exit_fraction: float | None = None
    partial_exit_fraction_column: str | None = None
    min_reward_risk_ratio: float | None = None
    min_reward_risk_ratio_column: str | None = None
    entry_type: Literal["market", "limit", "stop_market"] | None = None
    entry_type_column: str | None = None
    limit_offset_bps: float | None = None
    limit_offset_bps_column: str | None = None
    stop_offset_bps: float | None = None
    stop_offset_bps_column: str | None = None
    timeout_minutes: int | None = None
    timeout_minutes_column: str | None = None
    time_in_force: Literal["gtc", "gtd", "ioc", "fok"] | None = None
    time_in_force_column: str | None = None
    post_only: bool | None = None
    post_only_column: str | None = None
    reduce_only: bool | None = None
    reduce_only_column: str | None = None
    slippage_bps: float | None = None
    slippage_bps_column: str | None = None
    max_fill_fraction: float | None = None
    max_fill_fraction_column: str | None = None
    min_fill_fraction: float | None = None
    min_fill_fraction_column: str | None = None
    max_spread_bps: float | None = None
    max_spread_bps_column: str | None = None
    min_depth_usd: float | None = None
    min_depth_usd_column: str | None = None
    depth_column: str | None = None
    depth_participation_rate: float | None = None
    max_latency_ms: float | None = None
    max_latency_ms_column: str | None = None
    latency_column: str | None = None
    min_queue_position_score: float | None = None
    min_queue_position_score_column: str | None = None
    queue_position_score_column: str | None = None
    min_borrow_availability_ratio: float | None = None
    min_borrow_availability_ratio_column: str | None = None
    borrow_availability_column: str | None = None
    max_borrow_cost_bps: float | None = None
    max_borrow_cost_bps_column: str | None = None
    borrow_cost_column: str | None = None
    max_tax_drag_bps: float | None = None
    max_tax_drag_bps_column: str | None = None
    tax_drag_column: str | None = None
    max_turnover_pressure: float | None = None
    max_turnover_pressure_column: str | None = None
    turnover_pressure_column: str | None = None
    max_capacity_usage_ratio: float | None = None
    max_capacity_usage_ratio_column: str | None = None
    capacity_usage_column: str | None = None
    max_correlation_crowding_score: float | None = None
    max_correlation_crowding_score_column: str | None = None
    correlation_crowding_column: str | None = None
    min_fee_edge_bps: float | None = None
    min_fee_edge_bps_column: str | None = None
    fee_edge_column: str | None = None
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_multi_leg_entry(self) -> MultiLegEntry:
        if not self.real_market_symbol.strip():
            raise ValueError("rules.multi_leg.legs[].real_market_symbol must be non-empty")
        if self.position_weight < 0:
            raise ValueError("rules.multi_leg.legs[].position_weight must be >= 0")
        if self.notional_usd is not None and self.notional_usd < 0:
            raise ValueError("rules.multi_leg.legs[].notional_usd must be >= 0")
        for field_name in (
            "stop_loss_bps",
            "min_stop_loss_bps",
            "max_stop_loss_bps",
            "take_profit_bps",
            "min_take_profit_bps",
            "max_take_profit_bps",
            "trailing_stop_bps",
            "trailing_stop_activation_bps",
            "partial_take_profit_bps",
            "min_reward_risk_ratio",
            "limit_offset_bps",
            "stop_offset_bps",
            "slippage_bps",
            "max_spread_bps",
            "min_depth_usd",
            "max_latency_ms",
            "max_borrow_cost_bps",
            "max_tax_drag_bps",
            "max_turnover_pressure",
            "max_capacity_usage_ratio",
            "max_correlation_crowding_score",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.multi_leg.legs[].{field_name} must be >= 0")
        for field_name in (
            "max_fill_fraction",
            "min_fill_fraction",
            "depth_participation_rate",
            "min_queue_position_score",
            "min_borrow_availability_ratio",
        ):
            value = getattr(self, field_name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"rules.multi_leg.legs[].{field_name} must be between 0 and 1")
        if self.timeout_minutes is not None and self.timeout_minutes < 0:
            raise ValueError("rules.multi_leg.legs[].timeout_minutes must be >= 0")
        if (
            self.min_stop_loss_bps is not None
            and self.max_stop_loss_bps is not None
            and self.max_stop_loss_bps < self.min_stop_loss_bps
        ):
            raise ValueError(
                "rules.multi_leg.legs[].max_stop_loss_bps must be >= min_stop_loss_bps"
            )
        if (
            self.min_take_profit_bps is not None
            and self.max_take_profit_bps is not None
            and self.max_take_profit_bps < self.min_take_profit_bps
        ):
            raise ValueError(
                "rules.multi_leg.legs[].max_take_profit_bps must be >= min_take_profit_bps"
            )
        if self.partial_exit_fraction is not None and not 0.0 <= self.partial_exit_fraction <= 1.0:
            raise ValueError("rules.multi_leg.legs[].partial_exit_fraction must be between 0 and 1")
        for field_name in (
            "position_weight_column",
            "notional_usd_column",
            "stop_loss_bps_column",
            "min_stop_loss_bps_column",
            "max_stop_loss_bps_column",
            "take_profit_bps_column",
            "min_take_profit_bps_column",
            "max_take_profit_bps_column",
            "trailing_stop_bps_column",
            "trailing_stop_activation_bps_column",
            "partial_take_profit_bps_column",
            "partial_exit_fraction_column",
            "min_reward_risk_ratio_column",
            "entry_type_column",
            "limit_offset_bps_column",
            "stop_offset_bps_column",
            "timeout_minutes_column",
            "time_in_force_column",
            "post_only_column",
            "reduce_only_column",
            "slippage_bps_column",
            "max_fill_fraction_column",
            "min_fill_fraction_column",
            "max_spread_bps_column",
            "min_depth_usd_column",
            "depth_column",
            "max_latency_ms_column",
            "latency_column",
            "min_queue_position_score_column",
            "queue_position_score_column",
            "min_borrow_availability_ratio_column",
            "borrow_availability_column",
            "max_borrow_cost_bps_column",
            "borrow_cost_column",
            "max_tax_drag_bps_column",
            "tax_drag_column",
            "max_turnover_pressure_column",
            "turnover_pressure_column",
            "max_capacity_usage_ratio_column",
            "capacity_usage_column",
            "max_correlation_crowding_score_column",
            "correlation_crowding_column",
            "min_fee_edge_bps_column",
            "fee_edge_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.multi_leg.legs[].{field_name} must be non-empty when set")
        if (
            self.entry_type == "limit"
            and self.entry_type_column is None
            and self.limit_offset_bps is None
            and self.limit_offset_bps_column is None
        ):
            raise ValueError(
                "rules.multi_leg.legs[].limit_offset_bps or limit_offset_bps_column "
                "is required for limit entry"
            )
        if (
            self.entry_type == "stop_market"
            and self.entry_type_column is None
            and self.stop_offset_bps is None
            and self.stop_offset_bps_column is None
        ):
            raise ValueError(
                "rules.multi_leg.legs[].stop_offset_bps or stop_offset_bps_column "
                "is required for stop_market entry"
            )
        if (
            self.time_in_force == "gtd"
            and self.time_in_force_column is None
            and self.timeout_minutes is None
            and self.timeout_minutes_column is None
        ):
            raise ValueError(
                "rules.multi_leg.legs[].timeout_minutes or timeout_minutes_column "
                "is required when time_in_force is gtd"
            )
        if (
            self.time_in_force in {"ioc", "fok"}
            and self.time_in_force_column is None
            and (self.timeout_minutes is not None or self.timeout_minutes_column is not None)
        ):
            raise ValueError(
                "rules.multi_leg.legs[].timeout_minutes cannot be set when time_in_force is ioc or fok"
            )
        if (
            (self.post_only or self.post_only_column is not None)
            and self.entry_type_column is None
            and self.entry_type != "limit"
        ):
            raise ValueError("rules.multi_leg.legs[].post_only is only supported for limit entry")
        if self.reason_code is not None and not self.reason_code.strip():
            raise ValueError("rules.multi_leg.legs[].reason_code must be non-empty when set")
        self.real_market_symbol = self.real_market_symbol.strip().upper()
        return self


class MultiLegRules(BaseModel):
    enabled: bool = False
    anchor_real_market_symbol: str | None = None
    legs: list[MultiLegEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_multi_leg_rules(self) -> MultiLegRules:
        if self.anchor_real_market_symbol is not None:
            if not self.anchor_real_market_symbol.strip():
                raise ValueError("rules.multi_leg.anchor_real_market_symbol must be non-empty")
            self.anchor_real_market_symbol = self.anchor_real_market_symbol.strip().upper()
        if self.enabled:
            if self.anchor_real_market_symbol is None:
                raise ValueError("rules.multi_leg.anchor_real_market_symbol is required")
            if not self.legs:
                raise ValueError("rules.multi_leg.legs must not be empty when enabled")
        return self


class RegimeOverride(BaseModel):
    name: str
    when: EntryRules
    stop_loss_bps: float | None = None
    min_stop_loss_bps: float | None = None
    max_stop_loss_bps: float | None = None
    take_profit_bps: float | None = None
    min_take_profit_bps: float | None = None
    max_take_profit_bps: float | None = None
    trailing_stop_bps: float | None = None
    trailing_stop_activation_bps: float | None = None
    partial_take_profit_bps: float | None = None
    partial_exit_fraction: float | None = None
    min_reward_risk_ratio: float | None = None
    position_weight: float | None = None
    notional_usd: float | None = None
    slippage_bps: float | None = None
    max_fill_fraction: float | None = None
    min_fill_fraction: float | None = None
    max_spread_bps: float | None = None
    min_depth_usd: float | None = None
    depth_participation_rate: float | None = None
    max_latency_ms: float | None = None
    min_queue_position_score: float | None = None
    min_borrow_availability_ratio: float | None = None
    max_borrow_cost_bps: float | None = None
    max_tax_drag_bps: float | None = None
    max_turnover_pressure: float | None = None
    max_capacity_usage_ratio: float | None = None
    min_fee_edge_bps: float | None = None
    max_correlation_crowding_score: float | None = None

    @model_validator(mode="after")
    def validate_regime_override(self) -> RegimeOverride:
        if not self.name.strip():
            raise ValueError("rules.regime_overrides[].name must be non-empty")
        for field_name in (
            "stop_loss_bps",
            "min_stop_loss_bps",
            "max_stop_loss_bps",
            "take_profit_bps",
            "min_take_profit_bps",
            "max_take_profit_bps",
            "trailing_stop_bps",
            "trailing_stop_activation_bps",
            "partial_take_profit_bps",
            "min_reward_risk_ratio",
            "position_weight",
            "notional_usd",
            "slippage_bps",
            "max_spread_bps",
            "min_depth_usd",
            "max_latency_ms",
            "max_borrow_cost_bps",
            "max_tax_drag_bps",
            "max_turnover_pressure",
            "max_capacity_usage_ratio",
            "max_correlation_crowding_score",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.regime_overrides.{self.name}.{field_name} must be >= 0")
        for field_name in (
            "partial_exit_fraction",
            "max_fill_fraction",
            "min_fill_fraction",
            "depth_participation_rate",
            "min_queue_position_score",
            "min_borrow_availability_ratio",
        ):
            value = getattr(self, field_name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"rules.regime_overrides.{self.name}.{field_name} must be between 0 and 1"
                )
        return self
