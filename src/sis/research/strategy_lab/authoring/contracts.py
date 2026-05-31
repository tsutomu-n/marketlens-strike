from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.specs import SymbolBinding

EXIT_PRIORITY_ITEMS = (
    "break_even_stop",
    "stop_loss",
    "partial_take_profit",
    "take_profit",
    "trailing_stop",
    "time_stop",
)
DEFAULT_EXIT_PRIORITY = ",".join(EXIT_PRIORITY_ITEMS)

ALLOWED_OPERATORS = {
    "gt",
    "gte",
    "lt",
    "lte",
    "eq",
    "neq",
    "is_true",
    "is_false",
    "between",
    "in",
    "not_in",
    "crosses_above",
    "crosses_below",
    "rising",
    "falling",
    "consecutive_gt",
    "consecutive_gte",
    "consecutive_lt",
    "consecutive_lte",
    "consecutive_eq",
    "consecutive_neq",
}
VALID_THROUGH = {"signals", "backtest", "paper-preview"}


def _stable_digest(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


class AuthoringExperiment(BaseModel):
    strategy_id: str
    strategy_family: str = "declarative"
    strategy_version: str = "v1"
    description: str | None = None
    symbol_bindings: list[SymbolBinding]
    run_profile_id: str = "strategy_lab_research_only"

    @model_validator(mode="after")
    def validate_experiment(self) -> AuthoringExperiment:
        for name in ("strategy_id", "strategy_family", "strategy_version", "run_profile_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"experiment.{name} must be non-empty")
        if not self.symbol_bindings:
            raise ValueError("experiment.symbol_bindings must include at least one binding")
        return self


class ConfirmationPanel(BaseModel):
    path: str
    prefix: str
    max_age_minutes: int | None = None

    @model_validator(mode="after")
    def validate_confirmation_panel(self) -> ConfirmationPanel:
        if not self.path.strip():
            raise ValueError("data.confirmation_panels[].path must be non-empty")
        if not self.prefix.strip():
            raise ValueError("data.confirmation_panels[].prefix must be non-empty")
        self.prefix = self.prefix.strip()
        if self.prefix in {"ts", "canonical_symbol"}:
            raise ValueError("data.confirmation_panels[].prefix is reserved")
        if self.max_age_minutes is not None and self.max_age_minutes <= 0:
            raise ValueError("data.confirmation_panels[].max_age_minutes must be positive")
        return self


class AuthoringData(BaseModel):
    feature_panel_path: str = "data/research/feature_panel.parquet"
    quote_data_path: str = "data/normalized/quotes.parquet"
    cost_model_path: str = "data/research/venue_cost_matrix.csv"
    confirmation_panels: list[ConfirmationPanel] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_data(self) -> AuthoringData:
        prefixes = [panel.prefix for panel in self.confirmation_panels]
        if len(prefixes) != len(set(prefixes)):
            raise ValueError("data.confirmation_panels prefixes must be unique")
        return self


class Condition(BaseModel):
    column: str
    op: Literal[
        "gt",
        "gte",
        "lt",
        "lte",
        "eq",
        "neq",
        "is_true",
        "is_false",
        "between",
        "in",
        "not_in",
        "crosses_above",
        "crosses_below",
        "rising",
        "falling",
        "consecutive_gt",
        "consecutive_gte",
        "consecutive_lt",
        "consecutive_lte",
        "consecutive_eq",
        "consecutive_neq",
    ]
    value: Any = None
    value_column: str | None = None
    window: int | None = None

    @model_validator(mode="after")
    def validate_condition(self) -> Condition:
        if not self.column.strip():
            raise ValueError("rule condition column must be non-empty")
        if self.window is not None and self.window <= 0:
            raise ValueError(f"{self.column}: condition window must be positive")
        if self.value_column is not None and not self.value_column.strip():
            raise ValueError(f"{self.column}: value_column must be non-empty when set")
        if self.op in {"is_true", "is_false"} and self.value_column is not None:
            raise ValueError(f"{self.column}: {self.op} does not support value_column")
        if self.op in {"rising", "falling"}:
            if self.value is not None or self.value_column is not None:
                raise ValueError(f"{self.column}: {self.op} does not support value targets")
            return self
        if self.op == "between":
            if self.value_column is not None:
                raise ValueError(f"{self.column}: between does not support value_column")
            if not isinstance(self.value, list | tuple) or len(self.value) != 2:
                raise ValueError(f"{self.column}: between requires a two-item value")
        if self.op in {"in", "not_in"}:
            if self.value_column is not None:
                raise ValueError(f"{self.column}: {self.op} does not support value_column")
            if not isinstance(self.value, list | tuple | set) or len(self.value) == 0:
                raise ValueError(f"{self.column}: {self.op} requires a non-empty value list")
        if self.op in {"gt", "gte", "lt", "lte", "eq", "neq"}:
            has_value = self.value is not None
            has_value_column = self.value_column is not None
            if has_value == has_value_column:
                raise ValueError(
                    f"{self.column}: {self.op} requires exactly one of value or value_column"
                )
        if self.op in {
            "crosses_above",
            "crosses_below",
            "consecutive_gt",
            "consecutive_gte",
            "consecutive_lt",
            "consecutive_lte",
            "consecutive_eq",
            "consecutive_neq",
        }:
            has_value = self.value is not None
            has_value_column = self.value_column is not None
            if has_value == has_value_column:
                raise ValueError(
                    f"{self.column}: {self.op} requires exactly one of value or value_column"
                )
            if self.op.startswith("consecutive_") and self.window is None:
                raise ValueError(f"{self.column}: {self.op} requires condition window")
        return self


class EntryRules(BaseModel):
    all: list[Condition] = Field(default_factory=list)
    any: list[Condition] = Field(default_factory=list)
    none: list[Condition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entry(self) -> EntryRules:
        if not self.all and not self.any and not self.none:
            raise ValueError("rules.entry must include at least one all/any/none condition")
        return self


class ScoreTerm(BaseModel):
    column: str
    weight: float = 1.0

    @model_validator(mode="after")
    def validate_score_term(self) -> ScoreTerm:
        if not self.column.strip():
            raise ValueError("rules.score term column must be non-empty")
        if not math.isfinite(self.weight):
            raise ValueError("rules.score term weight must be finite")
        return self


class ModelScore(BaseModel):
    model_type: Literal["linear"] = "linear"
    intercept: float = 0.0
    coefficients: list[ScoreTerm] = Field(default_factory=list)
    activation: Literal["identity", "sigmoid", "tanh", "clamp_0_1"] = "identity"
    missing_value: float | None = None

    @model_validator(mode="after")
    def validate_model_score(self) -> ModelScore:
        if not math.isfinite(self.intercept):
            raise ValueError("rules.score.model_score.intercept must be finite")
        if self.missing_value is not None and not math.isfinite(self.missing_value):
            raise ValueError("rules.score.model_score.missing_value must be finite")
        if not self.coefficients:
            raise ValueError("rules.score.model_score.coefficients must not be empty")
        return self


class ScoreRules(BaseModel):
    weighted_sum: list[ScoreTerm] = Field(default_factory=list)
    model_score: ModelScore | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.weighted_sum) or self.model_score is not None


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


class PortfolioRules(BaseModel):
    max_signals_per_timestamp: int | None = None
    max_total_position_weight: float | None = None
    max_total_position_weight_column: str | None = None
    max_long_position_weight: float | None = None
    max_long_position_weight_column: str | None = None
    max_short_position_weight: float | None = None
    max_short_position_weight_column: str | None = None
    max_abs_net_position_weight: float | None = None
    max_abs_net_position_weight_column: str | None = None
    max_symbol_position_weight: float | None = None
    max_symbol_position_weight_column: str | None = None
    max_group_position_weight: float | None = None
    max_group_position_weight_column: str | None = None
    max_group_abs_net_position_weight: float | None = None
    max_group_abs_net_position_weight_column: str | None = None
    max_turnover_weight_per_timestamp: float | None = None
    turnover_weight_column: str | None = None
    group_column: str | None = None
    allocation_method: Literal[
        "none",
        "equal_weight",
        "score_proportional",
        "inverse_volatility",
        "dollar_neutral",
        "beta_neutral",
        "group_neutral",
    ] = "none"
    target_total_position_weight: float | None = None
    target_total_position_weight_column: str | None = None
    allocation_volatility_column: str | None = None
    allocation_beta_column: str | None = None

    @model_validator(mode="after")
    def validate_portfolio(self) -> PortfolioRules:
        if self.max_signals_per_timestamp is not None and self.max_signals_per_timestamp <= 0:
            raise ValueError("rules.portfolio.max_signals_per_timestamp must be positive")
        for field_name in (
            "max_total_position_weight",
            "max_long_position_weight",
            "max_short_position_weight",
            "max_abs_net_position_weight",
            "max_symbol_position_weight",
            "max_group_position_weight",
            "max_group_abs_net_position_weight",
            "max_turnover_weight_per_timestamp",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.portfolio.{field_name} must be >= 0")
        if self.turnover_weight_column is not None and not self.turnover_weight_column.strip():
            raise ValueError("rules.portfolio.turnover_weight_column must be non-empty when set")
        if (
            self.max_total_position_weight_column is not None
            and not self.max_total_position_weight_column.strip()
        ):
            raise ValueError(
                "rules.portfolio.max_total_position_weight_column must be non-empty when set"
            )
        for field_name in (
            "max_long_position_weight_column",
            "max_short_position_weight_column",
            "max_abs_net_position_weight_column",
            "max_symbol_position_weight_column",
            "max_group_position_weight_column",
            "max_group_abs_net_position_weight_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.portfolio.{field_name} must be non-empty when set")
        if (
            self.max_group_position_weight is not None
            or self.max_group_position_weight_column is not None
            or self.max_group_abs_net_position_weight is not None
            or self.max_group_abs_net_position_weight_column is not None
            or self.allocation_method == "group_neutral"
        ) and self.group_column is None:
            raise ValueError("rules.portfolio.group_column is required for group exposure limits")
        if self.group_column is not None and not self.group_column.strip():
            raise ValueError("rules.portfolio.group_column must be non-empty when set")
        if (
            self.group_column is not None
            and self.max_group_position_weight is None
            and self.max_group_position_weight_column is None
            and self.max_group_abs_net_position_weight is None
            and self.max_group_abs_net_position_weight_column is None
            and self.allocation_method != "group_neutral"
        ):
            raise ValueError(
                "rules.portfolio group exposure limit is required when group_column is set"
            )
        if self.target_total_position_weight is not None and self.target_total_position_weight < 0:
            raise ValueError("rules.portfolio.target_total_position_weight must be >= 0")
        if (
            self.allocation_method != "none"
            and self.target_total_position_weight is None
            and self.target_total_position_weight_column is None
        ):
            raise ValueError(
                "rules.portfolio.target_total_position_weight or target_total_position_weight_column "
                "is required when allocation_method is not none"
            )
        if (
            self.target_total_position_weight_column is not None
            and not self.target_total_position_weight_column.strip()
        ):
            raise ValueError(
                "rules.portfolio.target_total_position_weight_column must be non-empty when set"
            )
        if self.allocation_method == "inverse_volatility":
            if self.allocation_volatility_column is None:
                raise ValueError(
                    "rules.portfolio.allocation_volatility_column is required for inverse_volatility"
                )
            if not self.allocation_volatility_column.strip():
                raise ValueError("rules.portfolio.allocation_volatility_column must be non-empty")
        elif (
            self.allocation_volatility_column is not None
            and not self.allocation_volatility_column.strip()
        ):
            raise ValueError("rules.portfolio.allocation_volatility_column must be non-empty")
        if self.allocation_method == "beta_neutral":
            if self.allocation_beta_column is None:
                raise ValueError(
                    "rules.portfolio.allocation_beta_column is required for beta_neutral"
                )
            if not self.allocation_beta_column.strip():
                raise ValueError("rules.portfolio.allocation_beta_column must be non-empty")
        elif self.allocation_beta_column is not None and not self.allocation_beta_column.strip():
            raise ValueError("rules.portfolio.allocation_beta_column must be non-empty")
        return self

    @property
    def exposure_limits_enabled(self) -> bool:
        return any(
            value is not None
            for value in (
                self.max_total_position_weight,
                self.max_total_position_weight_column,
                self.max_long_position_weight,
                self.max_long_position_weight_column,
                self.max_short_position_weight,
                self.max_short_position_weight_column,
                self.max_abs_net_position_weight,
                self.max_abs_net_position_weight_column,
                self.max_symbol_position_weight,
                self.max_symbol_position_weight_column,
                self.max_group_position_weight,
                self.max_group_position_weight_column,
                self.max_group_abs_net_position_weight,
                self.max_group_abs_net_position_weight_column,
            )
        )


class PositionRules(BaseModel):
    max_open_signals_per_symbol: int | None = None
    max_open_position_weight_per_symbol: float | None = None
    holding_horizon_minutes: int | None = None
    require_open_position_for_markers: bool = False
    allow_opposing_open_positions: bool = True
    allow_pyramiding: bool = True

    @model_validator(mode="after")
    def validate_position(self) -> PositionRules:
        if self.max_open_signals_per_symbol is not None and self.max_open_signals_per_symbol <= 0:
            raise ValueError("rules.position.max_open_signals_per_symbol must be positive")
        if (
            self.max_open_position_weight_per_symbol is not None
            and self.max_open_position_weight_per_symbol < 0
        ):
            raise ValueError("rules.position.max_open_position_weight_per_symbol must be >= 0")
        if self.holding_horizon_minutes is not None and self.holding_horizon_minutes <= 0:
            raise ValueError("rules.position.holding_horizon_minutes must be positive")
        return self

    @property
    def enabled(self) -> bool:
        return (
            self.max_open_signals_per_symbol is not None
            or self.max_open_position_weight_per_symbol is not None
            or self.require_open_position_for_markers
            or not self.allow_opposing_open_positions
            or not self.allow_pyramiding
        )


class RiskThrottleRules(BaseModel):
    profile: Literal["none", "conservative", "strict"] = "none"
    max_drawdown_column: str | None = None
    max_drawdown_floor: float | None = None
    max_drawdown_floor_column: str | None = None
    daily_loss_column: str | None = None
    daily_loss_floor: float | None = None
    daily_loss_floor_column: str | None = None
    loss_streak_column: str | None = None
    max_loss_streak: int | None = None
    max_loss_streak_column: str | None = None
    cooldown_minutes: int | None = None

    @model_validator(mode="after")
    def validate_risk_throttle(self) -> RiskThrottleRules:
        if self.profile == "conservative":
            self.max_drawdown_column = self.max_drawdown_column or "strategy_drawdown"
            self.max_drawdown_floor = (
                -0.15 if self.max_drawdown_floor is None else self.max_drawdown_floor
            )
            self.daily_loss_column = self.daily_loss_column or "daily_pnl"
            self.daily_loss_floor = (
                -0.05 if self.daily_loss_floor is None else self.daily_loss_floor
            )
            self.loss_streak_column = self.loss_streak_column or "loss_streak"
            self.max_loss_streak = 3 if self.max_loss_streak is None else self.max_loss_streak
        elif self.profile == "strict":
            self.max_drawdown_column = self.max_drawdown_column or "strategy_drawdown"
            self.max_drawdown_floor = (
                -0.10 if self.max_drawdown_floor is None else self.max_drawdown_floor
            )
            self.daily_loss_column = self.daily_loss_column or "daily_pnl"
            self.daily_loss_floor = (
                -0.03 if self.daily_loss_floor is None else self.daily_loss_floor
            )
            self.loss_streak_column = self.loss_streak_column or "loss_streak"
            self.max_loss_streak = 2 if self.max_loss_streak is None else self.max_loss_streak
        if self.max_drawdown_column is None and (
            self.max_drawdown_floor is not None or self.max_drawdown_floor_column is not None
        ):
            raise ValueError(
                "rules.risk_throttle max_drawdown_column is required when max drawdown "
                "threshold is set"
            )
        if self.max_drawdown_column is not None and (
            self.max_drawdown_floor is None and self.max_drawdown_floor_column is None
        ):
            raise ValueError(
                "rules.risk_throttle max_drawdown_floor or max_drawdown_floor_column "
                "is required when max_drawdown_column is set"
            )
        if self.daily_loss_column is None and (
            self.daily_loss_floor is not None or self.daily_loss_floor_column is not None
        ):
            raise ValueError(
                "rules.risk_throttle daily_loss_column is required when daily loss threshold is set"
            )
        if self.daily_loss_column is not None and (
            self.daily_loss_floor is None and self.daily_loss_floor_column is None
        ):
            raise ValueError(
                "rules.risk_throttle daily_loss_floor or daily_loss_floor_column "
                "is required when daily_loss_column is set"
            )
        if self.loss_streak_column is None and (
            self.max_loss_streak is not None or self.max_loss_streak_column is not None
        ):
            raise ValueError(
                "rules.risk_throttle loss_streak_column is required when loss streak "
                "threshold is set"
            )
        if self.loss_streak_column is not None and (
            self.max_loss_streak is None and self.max_loss_streak_column is None
        ):
            raise ValueError(
                "rules.risk_throttle max_loss_streak or max_loss_streak_column "
                "is required when loss_streak_column is set"
            )
        if self.max_loss_streak is not None and self.max_loss_streak <= 0:
            raise ValueError("rules.risk_throttle.max_loss_streak must be positive")
        if self.cooldown_minutes is not None and self.cooldown_minutes <= 0:
            raise ValueError("rules.risk_throttle.cooldown_minutes must be positive")
        for field_name in (
            "max_drawdown_column",
            "max_drawdown_floor_column",
            "daily_loss_column",
            "daily_loss_floor_column",
            "loss_streak_column",
            "max_loss_streak_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.risk_throttle.{field_name} must be non-empty when set")
        return self

    @property
    def enabled(self) -> bool:
        return (
            self.profile != "none"
            or self.max_drawdown_column is not None
            or self.max_drawdown_floor_column is not None
            or self.daily_loss_column is not None
            or self.daily_loss_floor_column is not None
            or self.loss_streak_column is not None
            or self.max_loss_streak_column is not None
            or self.cooldown_minutes is not None
        )


class DataGuardRules(BaseModel):
    profile: Literal["none", "fresh_only", "quality_only", "strict"] = "none"
    max_feature_age_minutes: float | None = None
    max_feature_age_minutes_column: str | None = None
    feature_age_column: str | None = "feature_age_minutes"
    min_source_confidence: float | None = None
    min_source_confidence_column: str | None = None
    source_confidence_column: str | None = "source_confidence"
    min_venue_quality_score: float | None = None
    min_venue_quality_score_column: str | None = None
    venue_quality_score_column: str | None = "venue_quality_score"
    max_staleness_bps: float | None = None
    max_staleness_bps_column: str | None = None
    staleness_bps_column: str | None = "staleness_bps"
    max_regime_transition_score: float | None = None
    max_regime_transition_score_column: str | None = None
    regime_transition_score_column: str | None = "regime_transition_score"

    @model_validator(mode="after")
    def validate_data_guard(self) -> DataGuardRules:
        profile_defaults: dict[str, dict[str, float]] = {
            "fresh_only": {
                "max_feature_age_minutes": 60.0,
            },
            "quality_only": {
                "min_source_confidence": 0.70,
                "min_venue_quality_score": 0.70,
            },
            "strict": {
                "max_feature_age_minutes": 30.0,
                "min_source_confidence": 0.80,
                "min_venue_quality_score": 0.80,
                "max_staleness_bps": 5.0,
                "max_regime_transition_score": 0.50,
            },
        }
        for field_name, value in profile_defaults.get(self.profile, {}).items():
            if field_name not in self.model_fields_set:
                setattr(self, field_name, value)
        for field_name in (
            "max_feature_age_minutes",
            "max_staleness_bps",
            "max_regime_transition_score",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.data_guard.{field_name} must be >= 0")
        for field_name in ("min_source_confidence", "min_venue_quality_score"):
            value = getattr(self, field_name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"rules.data_guard.{field_name} must be between 0 and 1")
        for field_name in (
            "feature_age_column",
            "max_feature_age_minutes_column",
            "source_confidence_column",
            "min_source_confidence_column",
            "venue_quality_score_column",
            "min_venue_quality_score_column",
            "staleness_bps_column",
            "max_staleness_bps_column",
            "regime_transition_score_column",
            "max_regime_transition_score_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.data_guard.{field_name} must be non-empty when set")
        threshold_columns = (
            ("max_feature_age_minutes", "max_feature_age_minutes_column", "feature_age_column"),
            ("min_source_confidence", "min_source_confidence_column", "source_confidence_column"),
            (
                "min_venue_quality_score",
                "min_venue_quality_score_column",
                "venue_quality_score_column",
            ),
            ("max_staleness_bps", "max_staleness_bps_column", "staleness_bps_column"),
            (
                "max_regime_transition_score",
                "max_regime_transition_score_column",
                "regime_transition_score_column",
            ),
        )
        for threshold_field, threshold_column_field, value_column_field in threshold_columns:
            threshold_enabled = (
                getattr(self, threshold_field) is not None
                or getattr(self, threshold_column_field) is not None
            )
            if threshold_enabled and getattr(self, value_column_field) is None:
                raise ValueError(
                    f"rules.data_guard.{value_column_field} is required for {threshold_field}"
                )
        return self

    @property
    def enabled(self) -> bool:
        return any(
            value is not None
            for value in (
                self.max_feature_age_minutes,
                self.max_feature_age_minutes_column,
                self.min_source_confidence,
                self.min_source_confidence_column,
                self.min_venue_quality_score,
                self.min_venue_quality_score_column,
                self.max_staleness_bps,
                self.max_staleness_bps_column,
                self.max_regime_transition_score,
                self.max_regime_transition_score_column,
            )
        )


class TemporalRules(BaseModel):
    allowed_weekdays_utc: list[int] | None = None
    allowed_hours_utc: list[int] | None = None
    cooldown_minutes: int | None = None
    max_signals_per_symbol_per_day: int | None = None

    @model_validator(mode="after")
    def validate_temporal(self) -> TemporalRules:
        if self.allowed_weekdays_utc is not None:
            invalid = [value for value in self.allowed_weekdays_utc if value < 0 or value > 6]
            if invalid:
                raise ValueError("rules.temporal.allowed_weekdays_utc values must be 0..6")
        if self.allowed_hours_utc is not None:
            invalid = [value for value in self.allowed_hours_utc if value < 0 or value > 23]
            if invalid:
                raise ValueError("rules.temporal.allowed_hours_utc values must be 0..23")
        if self.cooldown_minutes is not None and self.cooldown_minutes < 0:
            raise ValueError("rules.temporal.cooldown_minutes must be >= 0")
        if (
            self.max_signals_per_symbol_per_day is not None
            and self.max_signals_per_symbol_per_day <= 0
        ):
            raise ValueError("rules.temporal.max_signals_per_symbol_per_day must be positive")
        return self

    @property
    def enabled(self) -> bool:
        return (
            self.allowed_weekdays_utc is not None
            or self.allowed_hours_utc is not None
            or self.cooldown_minutes is not None
            or self.max_signals_per_symbol_per_day is not None
        )


class EventWindowRule(BaseModel):
    name: str
    event_ts_column: str
    mode: Literal["allow", "block"] = "allow"
    before_minutes: int = 0
    after_minutes: int = 0
    block_reason: str | None = None

    @model_validator(mode="after")
    def validate_event_window(self) -> EventWindowRule:
        if not self.name.strip():
            raise ValueError("rules.event_windows[].name must be non-empty")
        if not self.event_ts_column.strip():
            raise ValueError("rules.event_windows[].event_ts_column must be non-empty")
        if self.before_minutes < 0 or self.after_minutes < 0:
            raise ValueError("rules.event_windows before_minutes/after_minutes must be >= 0")
        if self.block_reason is not None and not self.block_reason.strip():
            raise ValueError("rules.event_windows[].block_reason must be non-empty when set")
        return self


class CrossSectionalRules(BaseModel):
    long_top_n: int | None = None
    short_bottom_n: int | None = None
    long_top_fraction: float | None = None
    short_bottom_fraction: float | None = None
    group_column: str | None = None
    min_candidates: int | None = None
    min_long_score: float | None = None
    max_short_score: float | None = None

    @model_validator(mode="after")
    def validate_cross_sectional(self) -> CrossSectionalRules:
        if self.long_top_n is not None and self.long_top_n <= 0:
            raise ValueError("rules.cross_sectional.long_top_n must be positive")
        if self.short_bottom_n is not None and self.short_bottom_n <= 0:
            raise ValueError("rules.cross_sectional.short_bottom_n must be positive")
        if self.min_candidates is not None and self.min_candidates <= 0:
            raise ValueError("rules.cross_sectional.min_candidates must be positive")
        for field_name in ("long_top_fraction", "short_bottom_fraction"):
            value = getattr(self, field_name)
            if value is not None and (not math.isfinite(value) or value <= 0.0 or value > 1.0):
                raise ValueError(f"rules.cross_sectional.{field_name} must be in (0, 1]")
        if self.long_top_n is not None and self.long_top_fraction is not None:
            raise ValueError(
                "rules.cross_sectional.long_top_n and long_top_fraction are mutually exclusive"
            )
        if self.short_bottom_n is not None and self.short_bottom_fraction is not None:
            raise ValueError(
                "rules.cross_sectional.short_bottom_n and short_bottom_fraction are mutually exclusive"
            )
        if self.group_column is not None and not self.group_column.strip():
            raise ValueError("rules.cross_sectional.group_column must be non-empty when set")
        if (
            self.group_column is not None
            and self.long_top_n is None
            and self.short_bottom_n is None
            and self.long_top_fraction is None
            and self.short_bottom_fraction is None
        ):
            raise ValueError(
                "rules.cross_sectional top/bottom count or fraction is required when group_column is set"
            )
        for field_name in ("min_long_score", "max_short_score"):
            value = getattr(self, field_name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"rules.cross_sectional.{field_name} must be finite")
        return self

    @property
    def enabled(self) -> bool:
        return (
            self.long_top_n is not None
            or self.short_bottom_n is not None
            or self.long_top_fraction is not None
            or self.short_bottom_fraction is not None
        )


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


class DerivedFeature(BaseModel):
    name: str
    op: Literal[
        "add",
        "sub",
        "mul",
        "div",
        "ratio",
        "diff",
        "pct_diff",
        "abs",
        "neg",
        "max",
        "min",
        "mean",
        "true_range",
        "atr",
        "bollinger_upper",
        "bollinger_lower",
        "bollinger_width",
        "bollinger_percent_b",
        "donchian_upper",
        "donchian_lower",
        "donchian_mid",
        "donchian_width",
        "keltner_upper",
        "keltner_lower",
        "keltner_width",
        "ichimoku_conversion",
        "ichimoku_base",
        "ichimoku_span_a",
        "ichimoku_span_b",
        "macd_line",
        "stochastic_k",
        "stochastic_d",
        "adx",
        "obv",
        "volume_zscore",
        "ts_weekday",
        "ts_hour",
        "ts_month",
        "ts_day",
        "pct_change",
        "log_return",
        "lag",
        "rolling_return",
        "ewm_mean",
        "rsi",
        "rolling_min",
        "rolling_max",
        "rolling_sum",
        "rolling_mean",
        "rolling_std",
        "rolling_zscore",
        "rolling_percentile_rank",
        "rolling_volatility",
        "rolling_skew",
        "rolling_kurtosis",
        "annualized_volatility",
        "realized_variance",
        "downside_volatility",
        "sharpe_like",
        "sortino_like",
        "kelly_fraction",
        "historical_var",
        "expected_shortfall",
        "cumulative_return",
        "slope",
        "mean_reversion_score",
        "distance_from_ma",
        "rolling_corr",
        "rolling_beta",
        "rolling_spread_zscore",
        "tracking_error",
        "information_ratio",
        "rolling_autocorr",
        "order_flow_imbalance",
        "liquidity_depth_ratio",
        "spread_bps",
        "funding_bps",
        "carry_adjusted_return",
        "vol_risk_premium",
        "put_call_skew",
        "liquidity_stress",
        "net_exchange_flow",
        "onchain_activity_ratio",
        "sentiment_weighted_score",
        "event_surprise",
        "fundamental_value_gap",
        "risk_adjusted_score",
        "inverse_volatility_weight",
        "cross_sectional_rank",
        "cross_sectional_zscore",
        "cross_sectional_demean",
        "group_cross_sectional_rank",
        "group_cross_sectional_zscore",
        "group_cross_sectional_demean",
        "queue_position_score",
        "latency_penalty_bps",
        "maker_taker_fee_edge_bps",
        "borrow_cost_bps",
        "borrow_availability_ratio",
        "tax_drag_bps",
        "rebalance_drift",
        "freshness_score",
        "staleness_bps",
        "data_quality_blend",
        "ensemble_vote_count",
        "ensemble_vote_ratio",
        "regime_transition_score",
        "drawdown_from_peak",
        "rolling_max_drawdown",
        "drawdown_duration",
        "turnover_pressure",
        "capacity_usage_ratio",
        "correlation_crowding_score",
    ]
    columns: list[str] = Field(default_factory=list)
    value: float | None = None
    window: int | None = None
    fill_null: float | None = None

    @model_validator(mode="after")
    def validate_derived_feature(self) -> DerivedFeature:
        if not self.name.strip():
            raise ValueError("rules.derived_features[].name must be non-empty")
        if not self.columns or any(not column.strip() for column in self.columns):
            raise ValueError(f"rules.derived_features.{self.name}.columns must be non-empty")
        if self.op in {
            "abs",
            "neg",
            "bollinger_upper",
            "bollinger_lower",
            "bollinger_width",
            "bollinger_percent_b",
            "macd_line",
            "stochastic_d",
            "volume_zscore",
            "ts_weekday",
            "ts_hour",
            "ts_month",
            "ts_day",
            "pct_change",
            "log_return",
            "cumulative_return",
            "freshness_score",
            "staleness_bps",
            "drawdown_from_peak",
            "rolling_max_drawdown",
            "drawdown_duration",
            "lag",
            "rolling_return",
            "ewm_mean",
            "rsi",
            "rolling_min",
            "rolling_max",
            "rolling_sum",
            "rolling_mean",
            "rolling_std",
            "rolling_zscore",
            "rolling_percentile_rank",
            "rolling_volatility",
            "rolling_skew",
            "rolling_kurtosis",
            "annualized_volatility",
            "realized_variance",
            "downside_volatility",
            "sharpe_like",
            "sortino_like",
            "kelly_fraction",
            "historical_var",
            "expected_shortfall",
            "slope",
            "mean_reversion_score",
            "distance_from_ma",
            "rolling_autocorr",
        }:
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires one column"
                )
        if self.op in {"sub", "div", "ratio", "diff", "pct_diff"}:
            if len(self.columns) != 2 and self.value is None:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires two columns or value"
                )
        if self.op in {
            "rolling_corr",
            "rolling_beta",
            "rolling_spread_zscore",
            "tracking_error",
            "information_ratio",
        }:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires two columns"
                )
        if self.op in {
            "order_flow_imbalance",
            "liquidity_depth_ratio",
            "spread_bps",
            "carry_adjusted_return",
            "vol_risk_premium",
            "put_call_skew",
            "net_exchange_flow",
            "onchain_activity_ratio",
            "sentiment_weighted_score",
            "event_surprise",
            "fundamental_value_gap",
            "risk_adjusted_score",
            "group_cross_sectional_rank",
            "group_cross_sectional_zscore",
            "group_cross_sectional_demean",
            "queue_position_score",
            "maker_taker_fee_edge_bps",
            "borrow_cost_bps",
            "borrow_availability_ratio",
            "tax_drag_bps",
            "rebalance_drift",
            "regime_transition_score",
            "turnover_pressure",
            "capacity_usage_ratio",
            "correlation_crowding_score",
        }:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires two columns"
                )
        if self.op in {"data_quality_blend", "ensemble_vote_count", "ensemble_vote_ratio"}:
            if len(self.columns) < 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires at least one column"
                )
        if self.op == "latency_penalty_bps":
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.latency_penalty_bps requires one column"
                )
        if self.op in {
            "inverse_volatility_weight",
            "cross_sectional_rank",
            "cross_sectional_zscore",
            "cross_sectional_demean",
        }:
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires one column"
                )
        if self.op in {
            "group_cross_sectional_rank",
            "group_cross_sectional_zscore",
            "group_cross_sectional_demean",
        }:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires score and group columns"
                )
        if self.op == "funding_bps":
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.funding_bps requires one column"
                )
        if self.op == "liquidity_stress":
            if len(self.columns) != 3:
                raise ValueError(
                    f"rules.derived_features.{self.name}.liquidity_stress requires bid, ask, depth columns"
                )
        if self.op == "obv":
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.obv requires close and volume columns"
                )
        if self.op in {"donchian_upper", "donchian_lower", "donchian_mid", "donchian_width"}:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires high and low columns"
                )
        if self.op in {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_b"}:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires high and low columns"
                )
        if self.op == "ichimoku_span_a":
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.ichimoku_span_a requires conversion and base columns"
                )
        if self.op in {
            "true_range",
            "atr",
            "keltner_upper",
            "keltner_lower",
            "keltner_width",
            "stochastic_k",
            "adx",
        }:
            if len(self.columns) != 3:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires high, low, close columns"
                )
        if self.op in {
            "atr",
            "bollinger_upper",
            "bollinger_lower",
            "bollinger_width",
            "bollinger_percent_b",
            "donchian_upper",
            "donchian_lower",
            "donchian_mid",
            "donchian_width",
            "keltner_upper",
            "keltner_lower",
            "keltner_width",
            "ichimoku_conversion",
            "ichimoku_base",
            "ichimoku_span_b",
            "macd_line",
            "stochastic_k",
            "stochastic_d",
            "adx",
            "volume_zscore",
            "lag",
            "rolling_return",
            "ewm_mean",
            "rsi",
            "rolling_min",
            "rolling_max",
            "rolling_sum",
            "rolling_mean",
            "rolling_std",
            "rolling_zscore",
            "rolling_percentile_rank",
            "rolling_volatility",
            "rolling_skew",
            "rolling_kurtosis",
            "annualized_volatility",
            "realized_variance",
            "downside_volatility",
            "sharpe_like",
            "sortino_like",
            "kelly_fraction",
            "historical_var",
            "expected_shortfall",
            "slope",
            "mean_reversion_score",
            "distance_from_ma",
            "rolling_corr",
            "rolling_beta",
            "rolling_spread_zscore",
            "tracking_error",
            "information_ratio",
            "rolling_autocorr",
            "drawdown_from_peak",
            "rolling_max_drawdown",
            "drawdown_duration",
        }:
            if self.window is None or self.window <= 0:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires positive window"
                )
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError(f"rules.derived_features.{self.name}.value must be finite")
        if self.op in {
            "bollinger_upper",
            "bollinger_lower",
            "bollinger_width",
            "bollinger_percent_b",
            "keltner_upper",
            "keltner_lower",
            "keltner_width",
        } and (self.value is not None and self.value < 0):
            raise ValueError(
                f"rules.derived_features.{self.name}.{self.op} requires non-negative value"
            )
        if self.op == "macd_line" and (
            self.value is None or self.value <= 0 or self.value <= float(self.window or 0)
        ):
            raise ValueError(
                f"rules.derived_features.{self.name}.macd_line requires value greater than window"
            )
        if self.op in {
            "annualized_volatility",
            "sharpe_like",
            "sortino_like",
            "tracking_error",
            "information_ratio",
        } and (self.value is not None and self.value <= 0):
            raise ValueError(
                f"rules.derived_features.{self.name}.{self.op} requires positive value"
            )
        if self.op in {"historical_var", "expected_shortfall"} and (
            self.value is not None and not 0.0 < self.value < 1.0
        ):
            raise ValueError(
                f"rules.derived_features.{self.name}.{self.op} requires value between 0 and 1"
            )
        if self.fill_null is not None and not math.isfinite(self.fill_null):
            raise ValueError(f"rules.derived_features.{self.name}.fill_null must be finite")
        return self


class AuthoringRules(BaseModel):
    side: Literal["long", "short", "auto"] = "long"
    side_column: str | None = None
    timeframe: str = "4h"
    entry: EntryRules
    long_entry: EntryRules | None = None
    short_entry: EntryRules | None = None
    hold: EntryRules | None = None
    close: EntryRules | None = None
    reduce: EntryRules | None = None
    add: EntryRules | None = None
    rebalance: EntryRules | None = None
    exit: ExitRules = Field(default_factory=ExitRules)
    sizing: SizingRules = Field(default_factory=SizingRules)
    order: OrderRules = Field(default_factory=OrderRules)
    bracket: BracketRules = Field(default_factory=BracketRules)
    execution: ExecutionRules = Field(default_factory=ExecutionRules)
    portfolio: PortfolioRules = Field(default_factory=PortfolioRules)
    position: PositionRules = Field(default_factory=PositionRules)
    risk_throttle: RiskThrottleRules = Field(default_factory=RiskThrottleRules)
    data_guard: DataGuardRules = Field(default_factory=DataGuardRules)
    temporal: TemporalRules = Field(default_factory=TemporalRules)
    event_windows: list[EventWindowRule] = Field(default_factory=list)
    cross_sectional: CrossSectionalRules = Field(default_factory=CrossSectionalRules)
    multi_leg: MultiLegRules = Field(default_factory=MultiLegRules)
    derived_features: list[DerivedFeature] = Field(default_factory=list)
    regime_overrides: list[RegimeOverride] = Field(default_factory=list)
    score: ScoreRules = Field(default_factory=ScoreRules)
    confidence: float = 0.7
    reason_code: str = "declarative_rule"
    hold_reason_code: str = "hold_rule"
    close_reason_code: str = "close_rule"
    reduce_reason_code: str = "reduce_rule"
    add_reason_code: str = "add_rule"
    rebalance_reason_code: str = "rebalance_rule"

    @model_validator(mode="after")
    def validate_rules(self) -> AuthoringRules:
        if not self.timeframe.strip():
            raise ValueError("rules.timeframe must be non-empty")
        if self.side_column is not None and not self.side_column.strip():
            raise ValueError("rules.side_column must be non-empty when set")
        if (
            self.side == "auto"
            and not self.side_column
            and not self.long_entry
            and not self.short_entry
            and not self.cross_sectional.enabled
        ):
            raise ValueError(
                "rules.side=auto requires side_column, long_entry/short_entry, or cross_sectional"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("rules.confidence must be between 0 and 1")
        if not self.reason_code.strip():
            raise ValueError("rules.reason_code must be non-empty")
        if not self.hold_reason_code.strip():
            raise ValueError("rules.hold_reason_code must be non-empty")
        if not self.close_reason_code.strip():
            raise ValueError("rules.close_reason_code must be non-empty")
        if not self.reduce_reason_code.strip():
            raise ValueError("rules.reduce_reason_code must be non-empty")
        if not self.add_reason_code.strip():
            raise ValueError("rules.add_reason_code must be non-empty")
        if not self.rebalance_reason_code.strip():
            raise ValueError("rules.rebalance_reason_code must be non-empty")
        names = [feature.name for feature in self.derived_features]
        if len(names) != len(set(names)):
            raise ValueError("rules.derived_features names must be unique")
        regime_names = [regime.name for regime in self.regime_overrides]
        if len(regime_names) != len(set(regime_names)):
            raise ValueError("rules.regime_overrides names must be unique")
        event_names = [event.name for event in self.event_windows]
        if len(event_names) != len(set(event_names)):
            raise ValueError("rules.event_windows names must be unique")
        if self.cross_sectional.enabled and not self.score.enabled:
            raise ValueError(
                "rules.cross_sectional requires rules.score.weighted_sum or model_score"
            )
        if (
            self.bracket.enabled
            and not any(
                value is not None
                for value in (
                    self.exit.stop_loss_bps,
                    self.exit.stop_loss_bps_column,
                    self.exit.take_profit_bps,
                    self.exit.take_profit_bps_column,
                    self.exit.trailing_stop_bps,
                    self.exit.trailing_stop_bps_column,
                    self.bracket.time_stop_minutes,
                    self.bracket.time_stop_minutes_column,
                    self.bracket.break_even_after_bps,
                    self.bracket.break_even_after_bps_column,
                )
            )
            and not self.bracket.break_even_after_partial_take_profit
        ):
            raise ValueError("rules.bracket.enabled requires at least one exit control")
        if self.bracket.break_even_after_partial_take_profit and (
            (
                self.exit.partial_take_profit_bps is None
                and self.exit.partial_take_profit_bps_column is None
            )
            or (
                self.exit.partial_exit_fraction is None
                and self.exit.partial_exit_fraction_column is None
            )
        ):
            raise ValueError(
                "rules.bracket.break_even_after_partial_take_profit requires "
                "rules.exit.partial_take_profit_bps and partial_exit_fraction"
            )
        if (
            self.reduce is not None
            and self.exit.reduce_fraction is None
            and self.exit.reduce_fraction_column is None
        ):
            raise ValueError(
                "rules.exit.reduce_fraction or reduce_fraction_column is required when rules.reduce is set"
            )
        if (
            self.add is not None
            and self.exit.add_fraction is None
            and self.exit.add_fraction_column is None
        ):
            raise ValueError(
                "rules.exit.add_fraction or add_fraction_column is required when rules.add is set"
            )
        if (
            self.rebalance is not None
            and self.exit.rebalance_target_fraction is None
            and self.exit.rebalance_target_fraction_column is None
        ):
            raise ValueError(
                "rules.exit.rebalance_target_fraction or rebalance_target_fraction_column "
                "is required when rules.rebalance is set"
            )
        return self


class AuthoringBacktest(BaseModel):
    split_method: Literal["single_window", "walk_forward", "purged_walk_forward"] = (
        "purged_walk_forward"
    )
    era_unit: Literal["trading_day", "week", "month"] = "trading_day"
    label_horizon_minutes: int = 240
    purge_minutes: int = 0
    embargo_minutes: int = 0
    min_trade_count: int = 1
    primary_metric: str = "total_return"
    pass_thresholds: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_backtest(self) -> AuthoringBacktest:
        if self.label_horizon_minutes <= 0:
            raise ValueError("backtest.label_horizon_minutes must be positive")
        if self.purge_minutes < 0 or self.embargo_minutes < 0:
            raise ValueError("backtest purge/embargo minutes must be >= 0")
        if self.min_trade_count < 0:
            raise ValueError("backtest.min_trade_count must be >= 0")
        return self


ALLOWED_SWEEP_PATHS = {
    "rules.confidence",
    "rules.exit.stop_loss_bps",
    "rules.exit.min_stop_loss_bps",
    "rules.exit.max_stop_loss_bps",
    "rules.exit.take_profit_bps",
    "rules.exit.min_take_profit_bps",
    "rules.exit.max_take_profit_bps",
    "rules.exit.trailing_stop_bps",
    "rules.exit.trailing_stop_activation_bps",
    "rules.exit.partial_take_profit_bps",
    "rules.exit.partial_exit_fraction",
    "rules.exit.min_holding_minutes",
    "rules.exit.max_holding_minutes",
    "rules.sizing.position_weight",
    "rules.portfolio.max_signals_per_timestamp",
    "rules.risk_throttle.max_drawdown_floor",
    "rules.risk_throttle.daily_loss_floor",
    "rules.risk_throttle.max_loss_streak",
    "rules.risk_throttle.cooldown_minutes",
    "rules.data_guard.max_feature_age_minutes",
    "rules.data_guard.min_source_confidence",
    "rules.data_guard.min_venue_quality_score",
    "rules.data_guard.max_staleness_bps",
    "rules.data_guard.max_regime_transition_score",
    "rules.temporal.cooldown_minutes",
    "rules.temporal.max_signals_per_symbol_per_day",
    "rules.cross_sectional.long_top_n",
    "rules.cross_sectional.short_bottom_n",
    "rules.cross_sectional.long_top_fraction",
    "rules.cross_sectional.short_bottom_fraction",
    "rules.cross_sectional.min_candidates",
    "rules.cross_sectional.min_long_score",
    "rules.cross_sectional.max_short_score",
    "backtest.label_horizon_minutes",
}


class AuthoringOptimizer(BaseModel):
    parameter_sweep: dict[str, list[float | int | str]] = Field(default_factory=dict)
    selection_metric: str = "total_return"
    selection_direction: Literal["maximize", "minimize", "auto"] = "maximize"
    max_variants: int = 64

    @model_validator(mode="after")
    def validate_optimizer(self) -> AuthoringOptimizer:
        if self.max_variants <= 0:
            raise ValueError("optimizer.max_variants must be positive")
        for path, values in self.parameter_sweep.items():
            if path not in ALLOWED_SWEEP_PATHS:
                raise ValueError(f"optimizer.parameter_sweep unsupported path: {path}")
            if not values:
                raise ValueError(f"optimizer.parameter_sweep.{path} must not be empty")
        return self


class AuthoringPromotion(BaseModel):
    default_decision: Literal["hold", "reject"] = "hold"
    allow_paper_preview: bool = True


class StrategyAuthoringSpec(BaseModel):
    schema_version: Literal["strategy_authoring_spec.v1"]
    experiment: AuthoringExperiment
    data: AuthoringData = Field(default_factory=AuthoringData)
    rules: AuthoringRules
    backtest: AuthoringBacktest = Field(default_factory=AuthoringBacktest)
    optimizer: AuthoringOptimizer = Field(default_factory=AuthoringOptimizer)
    promotion: AuthoringPromotion = Field(default_factory=AuthoringPromotion)


class BundleMember(BaseModel):
    spec_path: str
    allocation_weight: float = 1.0
    enabled: bool = True

    @model_validator(mode="after")
    def validate_member(self) -> BundleMember:
        if not self.spec_path.strip():
            raise ValueError("bundle member spec_path must be non-empty")
        if self.allocation_weight < 0:
            raise ValueError("bundle member allocation_weight must be >= 0")
        return self


class BundlePortfolio(BaseModel):
    allocation_method: Literal["fixed_weight", "equal_weight", "risk_parity"] = "fixed_weight"
    max_total_allocation_weight: float | None = None
    selection_metric: str = "total_return"
    selection_direction: Literal["maximize", "minimize", "auto"] = "maximize"

    @model_validator(mode="after")
    def validate_portfolio(self) -> BundlePortfolio:
        if self.max_total_allocation_weight is not None and self.max_total_allocation_weight <= 0:
            raise ValueError("portfolio.max_total_allocation_weight must be positive")
        return self


class StrategyAuthoringBundleSpec(BaseModel):
    schema_version: Literal["strategy_authoring_bundle.v1"]
    bundle_id: str
    members: list[BundleMember]
    portfolio: BundlePortfolio = Field(default_factory=BundlePortfolio)

    @model_validator(mode="after")
    def validate_bundle(self) -> StrategyAuthoringBundleSpec:
        if not self.bundle_id.strip():
            raise ValueError("bundle_id must be non-empty")
        if not [member for member in self.members if member.enabled]:
            raise ValueError("bundle must include at least one enabled member")
        return self


class StrategyAuthoringValidationError(ValueError):
    pass


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for pivot_index in range(size):
        pivot_row = max(range(pivot_index, size), key=lambda row: abs(augmented[row][pivot_index]))
        if abs(augmented[pivot_row][pivot_index]) < 1e-12:
            raise StrategyAuthoringValidationError("model training matrix is singular")
        augmented[pivot_index], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_index]
        pivot = augmented[pivot_index][pivot_index]
        augmented[pivot_index] = [value / pivot for value in augmented[pivot_index]]
        for row in range(size):
            if row == pivot_index:
                continue
            factor = augmented[row][pivot_index]
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[pivot_index], strict=True)
            ]
    return [augmented[row][-1] for row in range(size)]
