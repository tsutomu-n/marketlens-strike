from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.authoring.contracts.base import EXIT_PRIORITY_ITEMS


class ExitRules(BaseModel):
    exit_on_opposite_signal: bool = False
    exit_on_close_signal: bool = False
    exit_on_reduce_signal: bool = False
    reduce_fraction: float | None = None
    reduce_fraction_column: str | None = None
    exit_on_add_signal: bool = False
    add_fraction: float | None = None
    add_fraction_column: str | None = None
    exit_on_rebalance_signal: bool = False
    rebalance_target_fraction: float | None = None
    rebalance_target_fraction_column: str | None = None
    rebalance_min_delta_fraction: float | None = None
    rebalance_min_delta_fraction_column: str | None = None
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
    min_reward_risk_ratio: float | None = None
    min_reward_risk_ratio_column: str | None = None
    trailing_stop_bps: float | None = None
    trailing_stop_bps_column: str | None = None
    trailing_stop_activation_bps: float | None = None
    trailing_stop_activation_bps_column: str | None = None
    partial_take_profit_bps: float | None = None
    partial_take_profit_bps_column: str | None = None
    partial_exit_fraction: float | None = None
    partial_exit_fraction_column: str | None = None
    min_holding_minutes: int | None = None
    min_holding_minutes_column: str | None = None
    max_holding_minutes: int | None = None
    max_holding_minutes_column: str | None = None
    exit_priority: list[str] = Field(default_factory=lambda: list(EXIT_PRIORITY_ITEMS))

    @model_validator(mode="after")
    def validate_exit(self) -> ExitRules:
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
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.exit.{field_name} must be >= 0")
        if self.partial_exit_fraction is not None and not 0.0 <= self.partial_exit_fraction <= 1.0:
            raise ValueError("rules.exit.partial_exit_fraction must be between 0 and 1")
        if self.reduce_fraction is not None and not 0.0 <= self.reduce_fraction <= 1.0:
            raise ValueError("rules.exit.reduce_fraction must be between 0 and 1")
        if self.add_fraction is not None and not 0.0 <= self.add_fraction <= 1.0:
            raise ValueError("rules.exit.add_fraction must be between 0 and 1")
        if self.rebalance_target_fraction is not None and self.rebalance_target_fraction < 0:
            raise ValueError("rules.exit.rebalance_target_fraction must be >= 0")
        if self.rebalance_min_delta_fraction is not None and self.rebalance_min_delta_fraction < 0:
            raise ValueError("rules.exit.rebalance_min_delta_fraction must be >= 0")
        if self.min_reward_risk_ratio is not None and self.min_reward_risk_ratio < 0:
            raise ValueError("rules.exit.min_reward_risk_ratio must be >= 0")
        if (
            self.min_stop_loss_bps is not None
            and self.max_stop_loss_bps is not None
            and self.max_stop_loss_bps < self.min_stop_loss_bps
        ):
            raise ValueError("rules.exit.max_stop_loss_bps must be >= min_stop_loss_bps")
        if (
            self.min_take_profit_bps is not None
            and self.max_take_profit_bps is not None
            and self.max_take_profit_bps < self.min_take_profit_bps
        ):
            raise ValueError("rules.exit.max_take_profit_bps must be >= min_take_profit_bps")
        if self.min_holding_minutes is not None and self.min_holding_minutes <= 0:
            raise ValueError("rules.exit.min_holding_minutes must be positive")
        if self.max_holding_minutes is not None and self.max_holding_minutes <= 0:
            raise ValueError("rules.exit.max_holding_minutes must be positive")
        if (
            self.min_holding_minutes is not None
            and self.max_holding_minutes is not None
            and self.max_holding_minutes < self.min_holding_minutes
        ):
            raise ValueError("rules.exit.max_holding_minutes must be >= min_holding_minutes")
        if len(set(self.exit_priority)) != len(self.exit_priority):
            raise ValueError("rules.exit.exit_priority must not contain duplicates")
        unsupported_exit_priority = [
            item for item in self.exit_priority if item not in EXIT_PRIORITY_ITEMS
        ]
        if unsupported_exit_priority:
            raise ValueError(
                f"rules.exit.exit_priority contains unsupported items: {unsupported_exit_priority}"
            )
        for field_name in (
            "stop_loss_bps_column",
            "min_stop_loss_bps_column",
            "max_stop_loss_bps_column",
            "take_profit_bps_column",
            "min_take_profit_bps_column",
            "max_take_profit_bps_column",
            "min_reward_risk_ratio_column",
            "trailing_stop_bps_column",
            "trailing_stop_activation_bps_column",
            "partial_take_profit_bps_column",
            "partial_exit_fraction_column",
            "min_holding_minutes_column",
            "max_holding_minutes_column",
            "reduce_fraction_column",
            "add_fraction_column",
            "rebalance_target_fraction_column",
            "rebalance_min_delta_fraction_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.exit.{field_name} must be non-empty when set")
        return self


class SizingRules(BaseModel):
    position_weight: float = 1.0
    position_weight_column: str | None = None
    notional_usd: float | None = None
    notional_usd_column: str | None = None
    volatility_target: float | None = None
    volatility_column: str | None = None
    max_volatility_scaled_position_weight: float | None = None

    @model_validator(mode="after")
    def validate_sizing(self) -> SizingRules:
        if self.position_weight < 0:
            raise ValueError("rules.sizing.position_weight must be >= 0")
        if self.notional_usd is not None and self.notional_usd < 0:
            raise ValueError("rules.sizing.notional_usd must be >= 0")
        if self.volatility_target is not None and self.volatility_target <= 0:
            raise ValueError("rules.sizing.volatility_target must be positive")
        if (
            self.max_volatility_scaled_position_weight is not None
            and self.max_volatility_scaled_position_weight < 0
        ):
            raise ValueError("rules.sizing.max_volatility_scaled_position_weight must be >= 0")
        if self.volatility_target is not None and self.volatility_column is None:
            raise ValueError("rules.sizing.volatility_column is required for volatility_target")
        for field_name in ("position_weight_column", "notional_usd_column", "volatility_column"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.sizing.{field_name} must be non-empty when set")
        return self


class OrderRules(BaseModel):
    entry_type: Literal["market", "limit", "stop_market"] = "market"
    entry_type_column: str | None = None
    limit_offset_bps: float | None = None
    limit_offset_bps_column: str | None = None
    stop_offset_bps: float | None = None
    stop_offset_bps_column: str | None = None
    timeout_minutes: int | None = None
    timeout_minutes_column: str | None = None
    time_in_force: Literal["gtc", "gtd", "ioc", "fok"] = "gtc"
    time_in_force_column: str | None = None
    post_only: bool = False
    post_only_column: str | None = None
    reduce_only: bool = False
    reduce_only_column: str | None = None

    @model_validator(mode="after")
    def validate_order(self) -> OrderRules:
        if (
            self.entry_type == "limit"
            and self.entry_type_column is None
            and self.limit_offset_bps is None
            and self.limit_offset_bps_column is None
        ):
            raise ValueError(
                "rules.order.limit_offset_bps or limit_offset_bps_column is required "
                "for limit entry"
            )
        if (
            self.entry_type == "stop_market"
            and self.entry_type_column is None
            and self.stop_offset_bps is None
            and self.stop_offset_bps_column is None
        ):
            raise ValueError(
                "rules.order.stop_offset_bps or stop_offset_bps_column is required "
                "for stop_market entry"
            )
        if (
            self.time_in_force == "gtd"
            and self.time_in_force_column is None
            and self.timeout_minutes is None
            and self.timeout_minutes_column is None
        ):
            raise ValueError(
                "rules.order.timeout_minutes or timeout_minutes_column is required "
                "when time_in_force is gtd"
            )
        if (
            self.time_in_force in {"ioc", "fok"}
            and self.time_in_force_column is None
            and (self.timeout_minutes is not None or self.timeout_minutes_column is not None)
        ):
            raise ValueError(
                "rules.order.timeout_minutes cannot be set when time_in_force is ioc or fok"
            )
        for field_name in ("limit_offset_bps", "stop_offset_bps"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.order.{field_name} must be >= 0")
        for field_name in (
            "entry_type_column",
            "limit_offset_bps_column",
            "stop_offset_bps_column",
            "timeout_minutes_column",
            "time_in_force_column",
            "post_only_column",
            "reduce_only_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.order.{field_name} must be non-empty when set")
        if (
            (self.post_only or self.post_only_column is not None)
            and self.entry_type_column is None
            and self.entry_type != "limit"
        ):
            raise ValueError("rules.order.post_only is only supported for limit entry")
        if self.timeout_minutes is not None and self.timeout_minutes < 0:
            raise ValueError("rules.order.timeout_minutes must be >= 0")
        return self


class BracketRules(BaseModel):
    enabled: bool = False
    bracket_type: Literal["oco"] = "oco"
    time_stop_minutes: int | None = None
    time_stop_minutes_column: str | None = None
    break_even_after_bps: float | None = None
    break_even_after_bps_column: str | None = None
    break_even_after_partial_take_profit: bool = False

    @model_validator(mode="after")
    def validate_bracket(self) -> BracketRules:
        if self.time_stop_minutes is not None and self.time_stop_minutes < 0:
            raise ValueError("rules.bracket.time_stop_minutes must be >= 0")
        if self.time_stop_minutes_column is not None and not self.time_stop_minutes_column.strip():
            raise ValueError("rules.bracket.time_stop_minutes_column must be non-empty when set")
        if self.break_even_after_bps is not None and self.break_even_after_bps < 0:
            raise ValueError("rules.bracket.break_even_after_bps must be >= 0")
        if (
            self.break_even_after_bps_column is not None
            and not self.break_even_after_bps_column.strip()
        ):
            raise ValueError("rules.bracket.break_even_after_bps_column must be non-empty when set")
        return self


class ExecutionRules(BaseModel):
    profile: Literal["none", "liquid_only", "balanced", "conservative"] = "none"
    slippage_bps: float = 0.0
    slippage_bps_column: str | None = None
    max_fill_fraction: float = 1.0
    max_fill_fraction_column: str | None = None
    min_fill_fraction: float | None = None
    min_fill_fraction_column: str | None = None
    max_spread_bps: float | None = None
    max_spread_bps_column: str | None = None
    min_depth_usd: float | None = None
    min_depth_usd_column: str | None = None
    depth_column: str | None = "min_side_depth_10bps_usd"
    depth_participation_rate: float = 1.0
    max_latency_ms: float | None = None
    max_latency_ms_column: str | None = None
    latency_column: str | None = "latency_ms"
    min_queue_position_score: float | None = None
    min_queue_position_score_column: str | None = None
    queue_position_score_column: str | None = "queue_position_score"
    min_borrow_availability_ratio: float | None = None
    min_borrow_availability_ratio_column: str | None = None
    borrow_availability_column: str | None = "borrow_availability_ratio"
    max_borrow_cost_bps: float | None = None
    max_borrow_cost_bps_column: str | None = None
    borrow_cost_column: str | None = "borrow_cost_bps"
    max_tax_drag_bps: float | None = None
    max_tax_drag_bps_column: str | None = None
    tax_drag_column: str | None = "tax_drag_bps"
    max_turnover_pressure: float | None = None
    max_turnover_pressure_column: str | None = None
    turnover_pressure_column: str | None = "turnover_pressure"
    max_capacity_usage_ratio: float | None = None
    max_capacity_usage_ratio_column: str | None = None
    capacity_usage_column: str | None = "capacity_usage_ratio"
    max_correlation_crowding_score: float | None = None
    max_correlation_crowding_score_column: str | None = None
    correlation_crowding_column: str | None = "correlation_crowding_score"
    min_fee_edge_bps: float | None = None
    min_fee_edge_bps_column: str | None = None
    fee_edge_column: str | None = "maker_taker_fee_edge_bps"

    @model_validator(mode="after")
    def validate_execution(self) -> ExecutionRules:
        profile_defaults: dict[str, dict[str, float]] = {
            "liquid_only": {
                "slippage_bps": 10.0,
                "max_fill_fraction": 1.0,
                "max_spread_bps": 30.0,
                "min_depth_usd": 50_000.0,
                "depth_participation_rate": 0.20,
            },
            "balanced": {
                "slippage_bps": 15.0,
                "max_fill_fraction": 0.75,
                "max_spread_bps": 20.0,
                "min_depth_usd": 100_000.0,
                "depth_participation_rate": 0.10,
                "max_latency_ms": 250.0,
                "min_queue_position_score": 0.30,
                "max_turnover_pressure": 0.80,
                "max_capacity_usage_ratio": 0.80,
                "max_correlation_crowding_score": 0.80,
            },
            "conservative": {
                "slippage_bps": 25.0,
                "max_fill_fraction": 0.50,
                "max_spread_bps": 10.0,
                "min_depth_usd": 250_000.0,
                "depth_participation_rate": 0.05,
                "max_latency_ms": 100.0,
                "min_queue_position_score": 0.60,
                "max_turnover_pressure": 0.40,
                "max_capacity_usage_ratio": 0.50,
                "max_correlation_crowding_score": 0.60,
                "min_fee_edge_bps": 0.0,
            },
        }
        for field_name, value in profile_defaults.get(self.profile, {}).items():
            if field_name not in self.model_fields_set:
                setattr(self, field_name, value)
        if self.slippage_bps < 0:
            raise ValueError("rules.execution.slippage_bps must be >= 0")
        if self.slippage_bps_column is not None and not self.slippage_bps_column.strip():
            raise ValueError("rules.execution.slippage_bps_column must be non-empty when set")
        if not 0.0 <= self.max_fill_fraction <= 1.0:
            raise ValueError("rules.execution.max_fill_fraction must be between 0 and 1")
        if self.max_fill_fraction_column is not None and not self.max_fill_fraction_column.strip():
            raise ValueError("rules.execution.max_fill_fraction_column must be non-empty when set")
        if self.min_fill_fraction is not None and not 0.0 <= self.min_fill_fraction <= 1.0:
            raise ValueError("rules.execution.min_fill_fraction must be between 0 and 1")
        if self.min_fill_fraction_column is not None and not self.min_fill_fraction_column.strip():
            raise ValueError("rules.execution.min_fill_fraction_column must be non-empty when set")
        if self.max_spread_bps is not None and self.max_spread_bps < 0:
            raise ValueError("rules.execution.max_spread_bps must be >= 0")
        if self.max_spread_bps_column is not None and not self.max_spread_bps_column.strip():
            raise ValueError("rules.execution.max_spread_bps_column must be non-empty when set")
        if self.min_depth_usd is not None and self.min_depth_usd < 0:
            raise ValueError("rules.execution.min_depth_usd must be >= 0")
        if self.min_depth_usd_column is not None and not self.min_depth_usd_column.strip():
            raise ValueError("rules.execution.min_depth_usd_column must be non-empty when set")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ValueError("rules.execution.max_latency_ms must be >= 0")
        if self.max_latency_ms_column is not None and not self.max_latency_ms_column.strip():
            raise ValueError("rules.execution.max_latency_ms_column must be non-empty when set")
        if self.max_latency_ms is not None and self.latency_column is None:
            raise ValueError("rules.execution.latency_column is required for max_latency_ms")
        if (
            self.min_queue_position_score is not None
            and not 0.0 <= self.min_queue_position_score <= 1.0
        ):
            raise ValueError("rules.execution.min_queue_position_score must be between 0 and 1")
        if (
            self.min_queue_position_score is not None
            or self.min_queue_position_score_column is not None
        ) and self.queue_position_score_column is None:
            raise ValueError(
                "rules.execution.queue_position_score_column is required for min_queue_position_score"
            )
        if (
            self.min_queue_position_score_column is not None
            and not self.min_queue_position_score_column.strip()
        ):
            raise ValueError(
                "rules.execution.min_queue_position_score_column must be non-empty when set"
            )
        if (
            self.min_borrow_availability_ratio is not None
            and not 0.0 <= self.min_borrow_availability_ratio <= 1.0
        ):
            raise ValueError(
                "rules.execution.min_borrow_availability_ratio must be between 0 and 1"
            )
        if (
            self.min_borrow_availability_ratio is not None
            or self.min_borrow_availability_ratio_column is not None
        ) and self.borrow_availability_column is None:
            raise ValueError(
                "rules.execution.borrow_availability_column is required for min_borrow_availability_ratio"
            )
        if (
            self.min_borrow_availability_ratio_column is not None
            and not self.min_borrow_availability_ratio_column.strip()
        ):
            raise ValueError(
                "rules.execution.min_borrow_availability_ratio_column must be non-empty when set"
            )
        if self.max_borrow_cost_bps is not None and self.max_borrow_cost_bps < 0:
            raise ValueError("rules.execution.max_borrow_cost_bps must be >= 0")
        if (
            self.max_borrow_cost_bps is not None or self.max_borrow_cost_bps_column is not None
        ) and self.borrow_cost_column is None:
            raise ValueError(
                "rules.execution.borrow_cost_column is required for max_borrow_cost_bps"
            )
        if (
            self.max_borrow_cost_bps_column is not None
            and not self.max_borrow_cost_bps_column.strip()
        ):
            raise ValueError(
                "rules.execution.max_borrow_cost_bps_column must be non-empty when set"
            )
        if self.max_tax_drag_bps is not None and self.max_tax_drag_bps < 0:
            raise ValueError("rules.execution.max_tax_drag_bps must be >= 0")
        if (
            self.max_tax_drag_bps is not None or self.max_tax_drag_bps_column is not None
        ) and self.tax_drag_column is None:
            raise ValueError("rules.execution.tax_drag_column is required for max_tax_drag_bps")
        if self.max_tax_drag_bps_column is not None and not self.max_tax_drag_bps_column.strip():
            raise ValueError("rules.execution.max_tax_drag_bps_column must be non-empty when set")
        if self.max_turnover_pressure is not None and self.max_turnover_pressure < 0:
            raise ValueError("rules.execution.max_turnover_pressure must be >= 0")
        if (
            self.max_turnover_pressure is not None or self.max_turnover_pressure_column is not None
        ) and self.turnover_pressure_column is None:
            raise ValueError(
                "rules.execution.turnover_pressure_column is required for max_turnover_pressure"
            )
        if (
            self.max_turnover_pressure_column is not None
            and not self.max_turnover_pressure_column.strip()
        ):
            raise ValueError(
                "rules.execution.max_turnover_pressure_column must be non-empty when set"
            )
        if self.max_capacity_usage_ratio is not None and self.max_capacity_usage_ratio < 0:
            raise ValueError("rules.execution.max_capacity_usage_ratio must be >= 0")
        if (
            self.max_capacity_usage_ratio is not None
            or self.max_capacity_usage_ratio_column is not None
        ) and self.capacity_usage_column is None:
            raise ValueError(
                "rules.execution.capacity_usage_column is required for max_capacity_usage_ratio"
            )
        if (
            self.max_capacity_usage_ratio_column is not None
            and not self.max_capacity_usage_ratio_column.strip()
        ):
            raise ValueError(
                "rules.execution.max_capacity_usage_ratio_column must be non-empty when set"
            )
        if (
            self.max_correlation_crowding_score is not None
            and self.max_correlation_crowding_score < 0
        ):
            raise ValueError("rules.execution.max_correlation_crowding_score must be >= 0")
        if (
            self.max_correlation_crowding_score is not None
            or self.max_correlation_crowding_score_column is not None
        ) and self.correlation_crowding_column is None:
            raise ValueError(
                "rules.execution.correlation_crowding_column is required for max_correlation_crowding_score"
            )
        if (
            self.max_correlation_crowding_score_column is not None
            and not self.max_correlation_crowding_score_column.strip()
        ):
            raise ValueError(
                "rules.execution.max_correlation_crowding_score_column must be non-empty when set"
            )
        if (
            self.min_fee_edge_bps is not None or self.min_fee_edge_bps_column is not None
        ) and self.fee_edge_column is None:
            raise ValueError("rules.execution.fee_edge_column is required for min_fee_edge_bps")
        if self.min_fee_edge_bps_column is not None and not self.min_fee_edge_bps_column.strip():
            raise ValueError("rules.execution.min_fee_edge_bps_column must be non-empty when set")
        if self.depth_column is not None and not self.depth_column.strip():
            raise ValueError("rules.execution.depth_column must be non-empty when set")
        if self.latency_column is not None and not self.latency_column.strip():
            raise ValueError("rules.execution.latency_column must be non-empty when set")
        if (
            self.queue_position_score_column is not None
            and not self.queue_position_score_column.strip()
        ):
            raise ValueError(
                "rules.execution.queue_position_score_column must be non-empty when set"
            )
        if (
            self.borrow_availability_column is not None
            and not self.borrow_availability_column.strip()
        ):
            raise ValueError(
                "rules.execution.borrow_availability_column must be non-empty when set"
            )
        if self.borrow_cost_column is not None and not self.borrow_cost_column.strip():
            raise ValueError("rules.execution.borrow_cost_column must be non-empty when set")
        if self.tax_drag_column is not None and not self.tax_drag_column.strip():
            raise ValueError("rules.execution.tax_drag_column must be non-empty when set")
        if self.turnover_pressure_column is not None and not self.turnover_pressure_column.strip():
            raise ValueError("rules.execution.turnover_pressure_column must be non-empty when set")
        if self.capacity_usage_column is not None and not self.capacity_usage_column.strip():
            raise ValueError("rules.execution.capacity_usage_column must be non-empty when set")
        if (
            self.correlation_crowding_column is not None
            and not self.correlation_crowding_column.strip()
        ):
            raise ValueError(
                "rules.execution.correlation_crowding_column must be non-empty when set"
            )
        if self.fee_edge_column is not None and not self.fee_edge_column.strip():
            raise ValueError("rules.execution.fee_edge_column must be non-empty when set")
        if not 0.0 <= self.depth_participation_rate <= 1.0:
            raise ValueError("rules.execution.depth_participation_rate must be between 0 and 1")
        return self
