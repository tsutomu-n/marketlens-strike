from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
from itertools import product
import json
import math
from pathlib import Path
from typing import Any, Iterable, Literal, cast

import polars as pl
from pydantic import BaseModel, Field, model_validator
import yaml

from sis.backtest.bridge import run_backtest_bridge_for_signals
from sis.backtest.signals import ResearchSignal
from sis.research.signal_builder import _legacy_export
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    empty_signal_artifact_run_id,
    empty_strategy_signal_frame,
    file_sha256,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
    write_strategy_signal_manifest,
)
from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.specs import SymbolBinding
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord

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
    stop_loss_bps: float | None = None
    stop_loss_bps_column: str | None = None
    take_profit_bps: float | None = None
    take_profit_bps_column: str | None = None
    trailing_stop_bps: float | None = None
    trailing_stop_bps_column: str | None = None
    partial_take_profit_bps: float | None = None
    partial_take_profit_bps_column: str | None = None
    partial_exit_fraction: float | None = None
    partial_exit_fraction_column: str | None = None
    min_holding_minutes: int | None = None

    @model_validator(mode="after")
    def validate_exit(self) -> ExitRules:
        for field_name in (
            "stop_loss_bps",
            "take_profit_bps",
            "trailing_stop_bps",
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
        if self.min_holding_minutes is not None and self.min_holding_minutes <= 0:
            raise ValueError("rules.exit.min_holding_minutes must be positive")
        for field_name in (
            "stop_loss_bps_column",
            "take_profit_bps_column",
            "trailing_stop_bps_column",
            "partial_take_profit_bps_column",
            "partial_exit_fraction_column",
            "reduce_fraction_column",
            "add_fraction_column",
            "rebalance_target_fraction_column",
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
    limit_offset_bps: float | None = None
    stop_offset_bps: float | None = None
    timeout_minutes: int | None = None
    time_in_force: Literal["gtc", "gtd", "ioc", "fok"] = "gtc"
    post_only: bool = False

    @model_validator(mode="after")
    def validate_order(self) -> OrderRules:
        if self.entry_type == "limit" and self.limit_offset_bps is None:
            raise ValueError("rules.order.limit_offset_bps is required for limit entry")
        if self.entry_type == "stop_market" and self.stop_offset_bps is None:
            raise ValueError("rules.order.stop_offset_bps is required for stop_market entry")
        if self.time_in_force == "gtd" and self.timeout_minutes is None:
            raise ValueError("rules.order.timeout_minutes is required when time_in_force is gtd")
        if self.time_in_force in {"ioc", "fok"} and self.timeout_minutes is not None:
            raise ValueError(
                "rules.order.timeout_minutes cannot be set when time_in_force is ioc or fok"
            )
        if self.post_only and self.entry_type != "limit":
            raise ValueError("rules.order.post_only is only supported for limit entry")
        for field_name in ("limit_offset_bps", "stop_offset_bps"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.order.{field_name} must be >= 0")
        if self.timeout_minutes is not None and self.timeout_minutes < 0:
            raise ValueError("rules.order.timeout_minutes must be >= 0")
        return self


class BracketRules(BaseModel):
    enabled: bool = False
    bracket_type: Literal["oco"] = "oco"
    time_stop_minutes: int | None = None
    break_even_after_bps: float | None = None

    @model_validator(mode="after")
    def validate_bracket(self) -> BracketRules:
        if self.time_stop_minutes is not None and self.time_stop_minutes < 0:
            raise ValueError("rules.bracket.time_stop_minutes must be >= 0")
        if self.break_even_after_bps is not None and self.break_even_after_bps < 0:
            raise ValueError("rules.bracket.break_even_after_bps must be >= 0")
        return self


class ExecutionRules(BaseModel):
    profile: Literal["none", "liquid_only", "balanced", "conservative"] = "none"
    slippage_bps: float = 0.0
    max_fill_fraction: float = 1.0
    max_spread_bps: float | None = None
    min_depth_usd: float | None = None
    depth_column: str | None = "min_side_depth_10bps_usd"
    depth_participation_rate: float = 1.0
    max_latency_ms: float | None = None
    latency_column: str | None = "latency_ms"
    min_queue_position_score: float | None = None
    queue_position_score_column: str | None = "queue_position_score"
    min_borrow_availability_ratio: float | None = None
    borrow_availability_column: str | None = "borrow_availability_ratio"
    max_borrow_cost_bps: float | None = None
    borrow_cost_column: str | None = "borrow_cost_bps"
    max_tax_drag_bps: float | None = None
    tax_drag_column: str | None = "tax_drag_bps"
    max_turnover_pressure: float | None = None
    turnover_pressure_column: str | None = "turnover_pressure"
    min_fee_edge_bps: float | None = None
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
                "min_fee_edge_bps": 0.0,
            },
        }
        for field_name, value in profile_defaults.get(self.profile, {}).items():
            if field_name not in self.model_fields_set:
                setattr(self, field_name, value)
        if self.slippage_bps < 0:
            raise ValueError("rules.execution.slippage_bps must be >= 0")
        if not 0.0 <= self.max_fill_fraction <= 1.0:
            raise ValueError("rules.execution.max_fill_fraction must be between 0 and 1")
        if self.max_spread_bps is not None and self.max_spread_bps < 0:
            raise ValueError("rules.execution.max_spread_bps must be >= 0")
        if self.min_depth_usd is not None and self.min_depth_usd < 0:
            raise ValueError("rules.execution.min_depth_usd must be >= 0")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ValueError("rules.execution.max_latency_ms must be >= 0")
        if self.max_latency_ms is not None and self.latency_column is None:
            raise ValueError("rules.execution.latency_column is required for max_latency_ms")
        if (
            self.min_queue_position_score is not None
            and not 0.0 <= self.min_queue_position_score <= 1.0
        ):
            raise ValueError("rules.execution.min_queue_position_score must be between 0 and 1")
        if self.min_queue_position_score is not None and self.queue_position_score_column is None:
            raise ValueError(
                "rules.execution.queue_position_score_column is required for min_queue_position_score"
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
            and self.borrow_availability_column is None
        ):
            raise ValueError(
                "rules.execution.borrow_availability_column is required for min_borrow_availability_ratio"
            )
        if self.max_borrow_cost_bps is not None and self.max_borrow_cost_bps < 0:
            raise ValueError("rules.execution.max_borrow_cost_bps must be >= 0")
        if self.max_borrow_cost_bps is not None and self.borrow_cost_column is None:
            raise ValueError(
                "rules.execution.borrow_cost_column is required for max_borrow_cost_bps"
            )
        if self.max_tax_drag_bps is not None and self.max_tax_drag_bps < 0:
            raise ValueError("rules.execution.max_tax_drag_bps must be >= 0")
        if self.max_tax_drag_bps is not None and self.tax_drag_column is None:
            raise ValueError("rules.execution.tax_drag_column is required for max_tax_drag_bps")
        if self.max_turnover_pressure is not None and self.max_turnover_pressure < 0:
            raise ValueError("rules.execution.max_turnover_pressure must be >= 0")
        if self.max_turnover_pressure is not None and self.turnover_pressure_column is None:
            raise ValueError(
                "rules.execution.turnover_pressure_column is required for max_turnover_pressure"
            )
        if self.min_fee_edge_bps is not None and self.fee_edge_column is None:
            raise ValueError("rules.execution.fee_edge_column is required for min_fee_edge_bps")
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
        if self.fee_edge_column is not None and not self.fee_edge_column.strip():
            raise ValueError("rules.execution.fee_edge_column must be non-empty when set")
        if not 0.0 <= self.depth_participation_rate <= 1.0:
            raise ValueError("rules.execution.depth_participation_rate must be between 0 and 1")
        return self


class PortfolioRules(BaseModel):
    max_signals_per_timestamp: int | None = None
    max_total_position_weight: float | None = None
    max_long_position_weight: float | None = None
    max_short_position_weight: float | None = None
    max_abs_net_position_weight: float | None = None
    max_symbol_position_weight: float | None = None
    max_group_position_weight: float | None = None
    max_group_abs_net_position_weight: float | None = None
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
            self.max_group_position_weight is not None
            or self.max_group_abs_net_position_weight is not None
            or self.allocation_method == "group_neutral"
        ) and self.group_column is None:
            raise ValueError("rules.portfolio.group_column is required for group exposure limits")
        if self.group_column is not None and not self.group_column.strip():
            raise ValueError("rules.portfolio.group_column must be non-empty when set")
        if (
            self.group_column is not None
            and self.max_group_position_weight is None
            and self.max_group_abs_net_position_weight is None
            and self.allocation_method != "group_neutral"
        ):
            raise ValueError(
                "rules.portfolio group exposure limit is required when group_column is set"
            )
        if self.target_total_position_weight is not None and self.target_total_position_weight < 0:
            raise ValueError("rules.portfolio.target_total_position_weight must be >= 0")
        if self.allocation_method != "none" and self.target_total_position_weight is None:
            raise ValueError(
                "rules.portfolio.target_total_position_weight is required when allocation_method is not none"
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
                self.max_long_position_weight,
                self.max_short_position_weight,
                self.max_abs_net_position_weight,
                self.max_symbol_position_weight,
                self.max_group_position_weight,
                self.max_group_abs_net_position_weight,
            )
        )


class PositionRules(BaseModel):
    max_open_signals_per_symbol: int | None = None
    max_open_position_weight_per_symbol: float | None = None
    holding_horizon_minutes: int | None = None

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
        )


class RiskThrottleRules(BaseModel):
    max_drawdown_column: str | None = None
    max_drawdown_floor: float | None = None
    daily_loss_column: str | None = None
    daily_loss_floor: float | None = None
    loss_streak_column: str | None = None
    max_loss_streak: int | None = None

    @model_validator(mode="after")
    def validate_risk_throttle(self) -> RiskThrottleRules:
        if (self.max_drawdown_column is None) != (self.max_drawdown_floor is None):
            raise ValueError(
                "rules.risk_throttle max_drawdown_column and max_drawdown_floor must be set together"
            )
        if (self.daily_loss_column is None) != (self.daily_loss_floor is None):
            raise ValueError(
                "rules.risk_throttle daily_loss_column and daily_loss_floor must be set together"
            )
        if (self.loss_streak_column is None) != (self.max_loss_streak is None):
            raise ValueError(
                "rules.risk_throttle loss_streak_column and max_loss_streak must be set together"
            )
        if self.max_loss_streak is not None and self.max_loss_streak <= 0:
            raise ValueError("rules.risk_throttle.max_loss_streak must be positive")
        for field_name in (
            "max_drawdown_column",
            "daily_loss_column",
            "loss_streak_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.risk_throttle.{field_name} must be non-empty when set")
        return self

    @property
    def enabled(self) -> bool:
        return (
            self.max_drawdown_column is not None
            or self.daily_loss_column is not None
            or self.loss_streak_column is not None
        )


class DataGuardRules(BaseModel):
    profile: Literal["none", "fresh_only", "quality_only", "strict"] = "none"
    max_feature_age_minutes: float | None = None
    feature_age_column: str | None = "feature_age_minutes"
    min_source_confidence: float | None = None
    source_confidence_column: str | None = "source_confidence"
    min_venue_quality_score: float | None = None
    venue_quality_score_column: str | None = "venue_quality_score"
    max_staleness_bps: float | None = None
    staleness_bps_column: str | None = "staleness_bps"
    max_regime_transition_score: float | None = None
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
            "source_confidence_column",
            "venue_quality_score_column",
            "staleness_bps_column",
            "regime_transition_score_column",
        ):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.data_guard.{field_name} must be non-empty when set")
        threshold_columns = (
            ("max_feature_age_minutes", "feature_age_column"),
            ("min_source_confidence", "source_confidence_column"),
            ("min_venue_quality_score", "venue_quality_score_column"),
            ("max_staleness_bps", "staleness_bps_column"),
            ("max_regime_transition_score", "regime_transition_score_column"),
        )
        for threshold_field, column_field in threshold_columns:
            if getattr(self, threshold_field) is not None and getattr(self, column_field) is None:
                raise ValueError(
                    f"rules.data_guard.{column_field} is required for {threshold_field}"
                )
        return self

    @property
    def enabled(self) -> bool:
        return any(
            value is not None
            for value in (
                self.max_feature_age_minutes,
                self.min_source_confidence,
                self.min_venue_quality_score,
                self.max_staleness_bps,
                self.max_regime_transition_score,
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
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_multi_leg_entry(self) -> MultiLegEntry:
        if not self.real_market_symbol.strip():
            raise ValueError("rules.multi_leg.legs[].real_market_symbol must be non-empty")
        if self.position_weight < 0:
            raise ValueError("rules.multi_leg.legs[].position_weight must be >= 0")
        if self.notional_usd is not None and self.notional_usd < 0:
            raise ValueError("rules.multi_leg.legs[].notional_usd must be >= 0")
        for field_name in ("position_weight_column", "notional_usd_column"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"rules.multi_leg.legs[].{field_name} must be non-empty when set")
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
    take_profit_bps: float | None = None
    trailing_stop_bps: float | None = None
    partial_take_profit_bps: float | None = None
    partial_exit_fraction: float | None = None
    position_weight: float | None = None
    notional_usd: float | None = None
    slippage_bps: float | None = None
    max_fill_fraction: float | None = None
    max_spread_bps: float | None = None
    min_depth_usd: float | None = None
    depth_participation_rate: float | None = None
    max_latency_ms: float | None = None
    min_queue_position_score: float | None = None
    min_borrow_availability_ratio: float | None = None
    max_borrow_cost_bps: float | None = None
    max_tax_drag_bps: float | None = None
    max_turnover_pressure: float | None = None
    min_fee_edge_bps: float | None = None

    @model_validator(mode="after")
    def validate_regime_override(self) -> RegimeOverride:
        if not self.name.strip():
            raise ValueError("rules.regime_overrides[].name must be non-empty")
        for field_name in (
            "stop_loss_bps",
            "take_profit_bps",
            "trailing_stop_bps",
            "partial_take_profit_bps",
            "position_weight",
            "notional_usd",
            "slippage_bps",
            "max_spread_bps",
            "min_depth_usd",
            "max_latency_ms",
            "max_borrow_cost_bps",
            "max_tax_drag_bps",
            "max_turnover_pressure",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"rules.regime_overrides.{self.name}.{field_name} must be >= 0")
        for field_name in (
            "partial_exit_fraction",
            "max_fill_fraction",
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
        if self.bracket.enabled and not any(
            value is not None
            for value in (
                self.exit.stop_loss_bps,
                self.exit.take_profit_bps,
                self.exit.trailing_stop_bps,
                self.bracket.time_stop_minutes,
                self.bracket.break_even_after_bps,
            )
        ):
            raise ValueError("rules.bracket.enabled requires at least one exit control")
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
    "rules.exit.take_profit_bps",
    "rules.exit.trailing_stop_bps",
    "rules.exit.partial_take_profit_bps",
    "rules.exit.partial_exit_fraction",
    "rules.exit.min_holding_minutes",
    "rules.sizing.position_weight",
    "rules.portfolio.max_signals_per_timestamp",
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
    selection_direction: Literal["maximize", "minimize"] = "maximize"
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
    selection_direction: Literal["maximize", "minimize"] = "maximize"

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


def load_authoring_spec(path: Path) -> StrategyAuthoringSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StrategyAuthoringValidationError("spec must be a YAML object")
    return StrategyAuthoringSpec.model_validate(payload)


def load_authoring_bundle_spec(path: Path) -> StrategyAuthoringBundleSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StrategyAuthoringValidationError("bundle spec must be a YAML object")
    return StrategyAuthoringBundleSpec.model_validate(payload)


def template_yaml() -> str:
    return """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: trend_pullback_user_v1
  strategy_family: trend_pullback
  strategy_version: v1
  description: Long only trend pullback example for Strategy Lab paper research.
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
      country: US
      currency: USD
  run_profile_id: strategy_lab_research_only
data:
  feature_panel_path: data/research/feature_panel.parquet
  quote_data_path: data/normalized/quotes.parquet
  cost_model_path: data/research/venue_cost_matrix.csv
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: close_above_sma20
        op: is_true
      - column: vix_level
        op: lt
        value: 30
    any:
      - column: research_return_1d
        op: gt
        value: 0
      - column: research_return_4h
        op: gt
        value: 0
  hold:
    any:
      - column: vix_level
        op: gte
        value: 30
  exit:
    stop_loss_bps: 150
    take_profit_bps: 300
    trailing_stop_bps: 120
    partial_take_profit_bps: 200
    partial_exit_fraction: 0.5
  sizing:
    position_weight: 1.0
    notional_usd: 1000
  portfolio:
    max_signals_per_timestamp: 3
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
  confidence: 0.7
  reason_code: trend_pullback_authoring_v1
  hold_reason_code: risk_hold_v1
backtest:
  split_method: purged_walk_forward
  era_unit: trading_day
  label_horizon_minutes: 240
  purge_minutes: 0
  embargo_minutes: 0
  min_trade_count: 1
  primary_metric: total_return
  pass_thresholds:
    max_drawdown: -0.2
optimizer:
  parameter_sweep:
    rules.exit.stop_loss_bps: [100, 150]
    rules.exit.take_profit_bps: [250, 300]
  selection_metric: total_return
  selection_direction: maximize
  max_variants: 8
promotion:
  default_decision: hold
  allow_paper_preview: true
"""


def write_template(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template_yaml(), encoding="utf-8")
    return path


def train_authoring_linear_model_score(
    spec: StrategyAuthoringSpec,
    *,
    data_dir: Path,
    target_column: str,
    feature_columns: list[str],
    ridge_lambda: float = 1e-6,
    activation: Literal["identity", "sigmoid", "tanh", "clamp_0_1"] = "identity",
    missing_value: float | None = None,
) -> dict[str, Any]:
    if not target_column.strip():
        raise StrategyAuthoringValidationError("target_column must be non-empty")
    if not feature_columns or any(not column.strip() for column in feature_columns):
        raise StrategyAuthoringValidationError("feature_columns must be non-empty")
    if ridge_lambda < 0:
        raise StrategyAuthoringValidationError("ridge_lambda must be >= 0")

    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    if not feature_path.exists():
        raise FileNotFoundError(f"feature_panel_path not found: {feature_path}")
    frame = _apply_derived_features(
        _apply_confirmation_panels(pl.read_parquet(feature_path), spec, data_dir=data_dir),
        spec,
    )
    required = {"canonical_symbol", target_column, *feature_columns}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise StrategyAuthoringValidationError(f"feature panel missing model columns: {missing}")

    symbols = {binding.real_market_symbol for binding in spec.experiment.symbol_bindings}
    rows: list[tuple[list[float], float]] = []
    for row in frame.to_dicts():
        if str(row.get("canonical_symbol") or "").upper() not in symbols:
            continue
        target = row.get(target_column)
        values = [row.get(column) for column in feature_columns]
        if not isinstance(target, int | float):
            continue
        if not all(isinstance(value, int | float) for value in values):
            continue
        numeric_values = cast(list[int | float], values)
        rows.append(([1.0, *[float(value) for value in numeric_values]], float(target)))
    if len(rows) < len(feature_columns) + 1:
        raise StrategyAuthoringValidationError(
            "not enough numeric rows to train linear model score"
        )

    dimension = len(feature_columns) + 1
    xtx = [[0.0 for _ in range(dimension)] for _ in range(dimension)]
    xty = [0.0 for _ in range(dimension)]
    for features, target in rows:
        for left in range(dimension):
            xty[left] += features[left] * target
            for right in range(dimension):
                xtx[left][right] += features[left] * features[right]
    for index in range(1, dimension):
        xtx[index][index] += ridge_lambda

    coefficients = _solve_linear_system(xtx, xty)
    model_score = {
        "model_type": "linear",
        "intercept": coefficients[0],
        "activation": activation,
        "missing_value": missing_value,
        "coefficients": [
            {"column": column, "weight": weight}
            for column, weight in zip(feature_columns, coefficients[1:], strict=True)
        ],
    }
    return {
        "schema_version": "strategy_authoring_model_score.v1",
        "paper_only": True,
        "live_order_submitted": False,
        "strategy_id": spec.experiment.strategy_id,
        "target_column": target_column,
        "row_count": len(rows),
        "ridge_lambda": ridge_lambda,
        "model_score": model_score,
    }


def write_authoring_model_score_outputs(
    spec: StrategyAuthoringSpec,
    payload: dict[str, Any],
    *,
    data_dir: Path,
    out_spec: Path | None = None,
) -> dict[str, Path]:
    payload_path = data_dir / "research/strategy_authoring_model_score.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    outputs = {"model_score": payload_path}
    if out_spec is not None:
        spec_payload = spec.model_dump(mode="json")
        spec_payload.setdefault("rules", {}).setdefault("score", {})["model_score"] = payload[
            "model_score"
        ]
        out_spec.parent.mkdir(parents=True, exist_ok=True)
        out_spec.write_text(yaml.safe_dump(spec_payload, sort_keys=False), encoding="utf-8")
        outputs["spec"] = out_spec
    return outputs


def _resolve_path(raw: str, data_dir: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "data":
        return data_dir.parent / path
    return path


def _prefixed_confirmation_columns(panel: ConfirmationPanel, columns: set[str]) -> set[str]:
    return {
        f"{panel.prefix}_{column}" for column in columns if column not in {"ts", "canonical_symbol"}
    }


def _required_columns(spec: StrategyAuthoringSpec) -> set[str]:
    columns = {"ts", "canonical_symbol"}
    derived_names = {feature.name for feature in spec.rules.derived_features}

    def add_column(column: str) -> None:
        if column not in derived_names:
            columns.add(column)

    def add_condition_columns(conditions: list[Condition]) -> None:
        for cond in conditions:
            add_column(cond.column)
            if cond.value_column is not None:
                add_column(cond.value_column)

    for feature in spec.rules.derived_features:
        for column in feature.columns:
            add_column(column)

    add_condition_columns([*spec.rules.entry.all, *spec.rules.entry.any, *spec.rules.entry.none])
    for entry in (spec.rules.long_entry, spec.rules.short_entry):
        if entry is not None:
            add_condition_columns([*entry.all, *entry.any, *entry.none])
    if spec.rules.hold is not None:
        add_condition_columns([*spec.rules.hold.all, *spec.rules.hold.any, *spec.rules.hold.none])
    if spec.rules.close is not None:
        add_condition_columns(
            [*spec.rules.close.all, *spec.rules.close.any, *spec.rules.close.none]
        )
    if spec.rules.reduce is not None:
        add_condition_columns(
            [*spec.rules.reduce.all, *spec.rules.reduce.any, *spec.rules.reduce.none]
        )
    if spec.rules.add is not None:
        add_condition_columns([*spec.rules.add.all, *spec.rules.add.any, *spec.rules.add.none])
    if spec.rules.rebalance is not None:
        add_condition_columns(
            [*spec.rules.rebalance.all, *spec.rules.rebalance.any, *spec.rules.rebalance.none]
        )
    for regime in spec.rules.regime_overrides:
        add_condition_columns([*regime.when.all, *regime.when.any, *regime.when.none])
    for term in spec.rules.score.weighted_sum:
        add_column(term.column)
    if spec.rules.score.model_score is not None:
        for term in spec.rules.score.model_score.coefficients:
            add_column(term.column)
    if spec.rules.side_column is not None:
        add_column(spec.rules.side_column)
    if spec.rules.exit.stop_loss_bps_column is not None:
        columns.add(spec.rules.exit.stop_loss_bps_column)
    if spec.rules.exit.take_profit_bps_column is not None:
        columns.add(spec.rules.exit.take_profit_bps_column)
    if spec.rules.exit.trailing_stop_bps_column is not None:
        columns.add(spec.rules.exit.trailing_stop_bps_column)
    if spec.rules.exit.partial_take_profit_bps_column is not None:
        columns.add(spec.rules.exit.partial_take_profit_bps_column)
    if spec.rules.exit.partial_exit_fraction_column is not None:
        columns.add(spec.rules.exit.partial_exit_fraction_column)
    if spec.rules.exit.reduce_fraction_column is not None:
        columns.add(spec.rules.exit.reduce_fraction_column)
    if spec.rules.exit.add_fraction_column is not None:
        columns.add(spec.rules.exit.add_fraction_column)
    if spec.rules.exit.rebalance_target_fraction_column is not None:
        columns.add(spec.rules.exit.rebalance_target_fraction_column)
    if spec.rules.sizing.position_weight_column is not None:
        columns.add(spec.rules.sizing.position_weight_column)
    if spec.rules.sizing.notional_usd_column is not None:
        columns.add(spec.rules.sizing.notional_usd_column)
    if spec.rules.sizing.volatility_column is not None:
        columns.add(spec.rules.sizing.volatility_column)
    if (
        spec.rules.execution.max_latency_ms is not None
        and spec.rules.execution.latency_column is not None
    ):
        add_column(spec.rules.execution.latency_column)
    if (
        spec.rules.execution.min_queue_position_score is not None
        and spec.rules.execution.queue_position_score_column is not None
    ):
        add_column(spec.rules.execution.queue_position_score_column)
    if (
        spec.rules.execution.min_borrow_availability_ratio is not None
        and spec.rules.execution.borrow_availability_column is not None
    ):
        add_column(spec.rules.execution.borrow_availability_column)
    if (
        spec.rules.execution.max_borrow_cost_bps is not None
        and spec.rules.execution.borrow_cost_column is not None
    ):
        add_column(spec.rules.execution.borrow_cost_column)
    if (
        spec.rules.execution.max_tax_drag_bps is not None
        and spec.rules.execution.tax_drag_column is not None
    ):
        add_column(spec.rules.execution.tax_drag_column)
    if (
        spec.rules.execution.max_turnover_pressure is not None
        and spec.rules.execution.turnover_pressure_column is not None
    ):
        add_column(spec.rules.execution.turnover_pressure_column)
    if (
        spec.rules.execution.min_fee_edge_bps is not None
        and spec.rules.execution.fee_edge_column is not None
    ):
        add_column(spec.rules.execution.fee_edge_column)
    if spec.rules.portfolio.allocation_volatility_column is not None:
        columns.add(spec.rules.portfolio.allocation_volatility_column)
    if spec.rules.portfolio.allocation_beta_column is not None:
        columns.add(spec.rules.portfolio.allocation_beta_column)
    if spec.rules.portfolio.group_column is not None:
        columns.add(spec.rules.portfolio.group_column)
    if spec.rules.portfolio.turnover_weight_column is not None:
        columns.add(spec.rules.portfolio.turnover_weight_column)
    if spec.rules.cross_sectional.group_column is not None:
        columns.add(spec.rules.cross_sectional.group_column)
    if spec.rules.risk_throttle.max_drawdown_column is not None:
        columns.add(spec.rules.risk_throttle.max_drawdown_column)
    if spec.rules.risk_throttle.daily_loss_column is not None:
        columns.add(spec.rules.risk_throttle.daily_loss_column)
    if spec.rules.risk_throttle.loss_streak_column is not None:
        columns.add(spec.rules.risk_throttle.loss_streak_column)
    data_guard = spec.rules.data_guard
    if data_guard.max_feature_age_minutes is not None and data_guard.feature_age_column is not None:
        columns.add(data_guard.feature_age_column)
    if (
        data_guard.min_source_confidence is not None
        and data_guard.source_confidence_column is not None
    ):
        columns.add(data_guard.source_confidence_column)
    if (
        data_guard.min_venue_quality_score is not None
        and data_guard.venue_quality_score_column is not None
    ):
        columns.add(data_guard.venue_quality_score_column)
    if data_guard.max_staleness_bps is not None and data_guard.staleness_bps_column is not None:
        columns.add(data_guard.staleness_bps_column)
    if (
        data_guard.max_regime_transition_score is not None
        and data_guard.regime_transition_score_column is not None
    ):
        columns.add(data_guard.regime_transition_score_column)
    for event_window in spec.rules.event_windows:
        columns.add(event_window.event_ts_column)
    for leg in spec.rules.multi_leg.legs:
        if leg.position_weight_column is not None:
            columns.add(leg.position_weight_column)
        if leg.notional_usd_column is not None:
            columns.add(leg.notional_usd_column)
    return columns


def _all_conditions(spec: StrategyAuthoringSpec) -> list[Condition]:
    groups = [
        spec.rules.entry,
        spec.rules.long_entry,
        spec.rules.short_entry,
        spec.rules.hold,
        spec.rules.close,
        spec.rules.reduce,
        spec.rules.add,
        spec.rules.rebalance,
        *(regime.when for regime in spec.rules.regime_overrides),
    ]
    conditions: list[Condition] = []
    for group in groups:
        if group is not None:
            conditions.extend([*group.all, *group.any, *group.none])
    return conditions


def validate_authoring_inputs(spec: StrategyAuthoringSpec, *, data_dir: Path) -> list[str]:
    errors: list[str] = []
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    if not feature_path.exists():
        errors.append(f"feature_panel_path not found: {feature_path}")
        return errors
    try:
        feature = pl.read_parquet(feature_path, n_rows=1)
    except Exception as exc:  # pragma: no cover - polars gives version-specific exceptions
        errors.append(f"feature_panel_path is not readable parquet: {exc}")
        return errors
    available_columns = set(feature.columns)
    for panel in spec.data.confirmation_panels:
        panel_path = _resolve_path(panel.path, data_dir)
        if not panel_path.exists():
            errors.append(f"confirmation panel not found: {panel_path}")
            continue
        try:
            panel_frame = pl.read_parquet(panel_path, n_rows=1)
        except Exception as exc:  # pragma: no cover - polars gives version-specific exceptions
            errors.append(f"confirmation panel is not readable parquet: {panel_path}: {exc}")
            continue
        required_panel_columns = {"ts", "canonical_symbol"}
        missing_panel_columns = sorted(required_panel_columns.difference(panel_frame.columns))
        if missing_panel_columns:
            errors.append(
                f"confirmation panel missing columns: {panel_path}: {missing_panel_columns}"
            )
            continue
        available_columns.update(_prefixed_confirmation_columns(panel, set(panel_frame.columns)))
    missing = sorted(_required_columns(spec).difference(available_columns))
    if missing:
        errors.append(f"feature panel missing columns: {missing}")
    generated: set[str] = set()
    base_columns = available_columns
    for derived in spec.rules.derived_features:
        available = base_columns.union(generated)
        missing_inputs = sorted(set(derived.columns).difference(available))
        if missing_inputs:
            errors.append(f"derived feature {derived.name} missing input columns: {missing_inputs}")
        generated.add(derived.name)
    binding_symbols = {binding.real_market_symbol for binding in spec.experiment.symbol_bindings}
    if spec.rules.multi_leg.enabled:
        symbols = {str(spec.rules.multi_leg.anchor_real_market_symbol)}
        leg_symbols = {leg.real_market_symbol for leg in spec.rules.multi_leg.legs}
        missing_bindings = sorted(leg_symbols.union(symbols).difference(binding_symbols))
        if missing_bindings:
            errors.append(f"multi_leg symbols missing symbol_bindings: {missing_bindings}")
    else:
        symbols = binding_symbols
    if "canonical_symbol" in feature.columns:
        full = pl.read_parquet(feature_path, columns=["canonical_symbol"])
        observed = {str(value).upper() for value in full.get_column("canonical_symbol").to_list()}
        missing_symbols = sorted(symbols.difference(observed))
        if missing_symbols:
            errors.append(f"feature panel missing real_market_symbol rows: {missing_symbols}")
    return errors


ADVANCED_CONDITION_OPERATORS = {
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


def _condition_feature_name(condition: Condition) -> str:
    payload = condition.model_dump(mode="json", exclude_none=True)
    return f"__condition_{_stable_digest(payload)}"


def _condition_target_expr(condition: Condition) -> pl.Expr:
    return (
        pl.col(condition.value_column)
        if condition.value_column is not None
        else pl.lit(condition.value)
    )


def _condition_comparison_expr(condition: Condition) -> pl.Expr:
    target = _condition_target_expr(condition)
    value = pl.col(condition.column)
    op = condition.op.removeprefix("consecutive_")
    if op == "gt":
        return value > target
    if op == "gte":
        return value >= target
    if op == "lt":
        return value < target
    if op == "lte":
        return value <= target
    if op == "eq":
        return value == target
    if op == "neq":
        return value != target
    raise StrategyAuthoringValidationError(f"Unsupported advanced comparison: {condition.op}")


def _condition_feature_expr(condition: Condition) -> pl.Expr:
    value = pl.col(condition.column)
    if condition.op in {"crosses_above", "crosses_below"}:
        target = _condition_target_expr(condition)
        previous_value = value.shift(1).over("canonical_symbol")
        previous_target = (
            pl.col(condition.value_column).shift(1).over("canonical_symbol")
            if condition.value_column is not None
            else pl.lit(condition.value)
        )
        if condition.op == "crosses_above":
            expr = (value > target) & (previous_value <= previous_target)
        else:
            expr = (value < target) & (previous_value >= previous_target)
    elif condition.op in {"rising", "falling"}:
        previous_value = value.shift(condition.window or 1).over("canonical_symbol")
        expr = value > previous_value if condition.op == "rising" else value < previous_value
    elif condition.op.startswith("consecutive_"):
        base = _condition_comparison_expr(condition).cast(pl.Int8)
        expr = (
            base.rolling_min(window_size=condition.window or 1, min_samples=condition.window or 1)
            .over("canonical_symbol")
            .fill_null(0)
            == 1
        )
    else:
        raise StrategyAuthoringValidationError(f"Unsupported advanced condition: {condition.op}")
    return expr.fill_null(False).alias(_condition_feature_name(condition))


def _apply_condition_features(frame: pl.DataFrame, spec: StrategyAuthoringSpec) -> pl.DataFrame:
    conditions = [
        condition
        for condition in _all_conditions(spec)
        if condition.op in ADVANCED_CONDITION_OPERATORS
    ]
    if not conditions:
        return frame
    enriched = frame.sort(["canonical_symbol", "ts"])
    seen: set[str] = set()
    for condition in conditions:
        name = _condition_feature_name(condition)
        if name in seen:
            continue
        seen.add(name)
        enriched = enriched.with_columns(_condition_feature_expr(condition))
    return enriched


def _condition_passes(row: dict[str, Any], condition: Condition) -> bool:
    if condition.op in ADVANCED_CONDITION_OPERATORS:
        return bool(row.get(_condition_feature_name(condition)))
    value = row.get(condition.column)
    if condition.op == "is_true":
        return value is True
    if condition.op == "is_false":
        return value is False
    if value is None:
        return False
    target = (
        row.get(condition.value_column) if condition.value_column is not None else condition.value
    )
    if target is None:
        return False
    if condition.op == "gt":
        return value > target
    if condition.op == "gte":
        return value >= target
    if condition.op == "lt":
        return value < target
    if condition.op == "lte":
        return value <= target
    if condition.op == "eq":
        return value == target
    if condition.op == "neq":
        return value != target
    if condition.op == "between":
        low, high = target
        return low <= value <= high
    if condition.op == "in":
        return value in target
    if condition.op == "not_in":
        return value not in target
    raise StrategyAuthoringValidationError(f"Unsupported operator: {condition.op}")


def _literal_or_col(feature: DerivedFeature, index: int = 1) -> pl.Expr:
    if len(feature.columns) > index:
        return pl.col(feature.columns[index])
    if feature.value is None:
        raise StrategyAuthoringValidationError(
            f"derived feature {feature.name} requires column {index + 1} or value"
        )
    return pl.lit(feature.value)


def _safe_denominator(expr: pl.Expr) -> pl.Expr:
    return pl.when(expr == 0).then(None).otherwise(expr)


def _derived_expression(feature: DerivedFeature) -> pl.Expr:
    first = pl.col(feature.columns[0])
    if feature.op == "add":
        expr = first
        for column in feature.columns[1:]:
            expr = expr + pl.col(column)
        if feature.value is not None:
            expr = expr + feature.value
    elif feature.op == "sub":
        expr = first - _literal_or_col(feature)
    elif feature.op == "mul":
        expr = first
        for column in feature.columns[1:]:
            expr = expr * pl.col(column)
        if feature.value is not None:
            expr = expr * feature.value
    elif feature.op in {"div", "ratio"}:
        denominator = _literal_or_col(feature)
        expr = first / _safe_denominator(denominator)
    elif feature.op == "diff":
        expr = first - _literal_or_col(feature)
    elif feature.op == "pct_diff":
        denominator = _literal_or_col(feature)
        expr = (first - denominator) / _safe_denominator(denominator)
    elif feature.op == "abs":
        expr = first.abs()
    elif feature.op == "neg":
        expr = -first
    elif feature.op == "max":
        expr = pl.max_horizontal([pl.col(column) for column in feature.columns])
        if feature.value is not None:
            expr = pl.max_horizontal([expr, pl.lit(feature.value)])
    elif feature.op == "min":
        expr = pl.min_horizontal([pl.col(column) for column in feature.columns])
        if feature.value is not None:
            expr = pl.min_horizontal([expr, pl.lit(feature.value)])
    elif feature.op == "mean":
        expressions = [pl.col(column) for column in feature.columns]
        if feature.value is not None:
            expressions.append(pl.lit(feature.value))
        expr = pl.mean_horizontal(expressions)
    elif feature.op in {"true_range", "atr"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        close = pl.col(feature.columns[2])
        previous_close = close.shift(1).over("canonical_symbol")
        true_range = pl.max_horizontal(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ]
        )
        expr = (
            true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            if feature.op == "atr"
            else true_range
        )
    elif feature.op in {
        "bollinger_upper",
        "bollinger_lower",
        "bollinger_width",
        "bollinger_percent_b",
    }:
        multiplier = feature.value if feature.value is not None else 2.0
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        upper = mean + (std * multiplier)
        lower = mean - (std * multiplier)
        if feature.op == "bollinger_upper":
            expr = upper
        elif feature.op == "bollinger_lower":
            expr = lower
        elif feature.op == "bollinger_width":
            expr = (upper - lower) / _safe_denominator(mean)
        else:
            expr = (first - lower) / _safe_denominator(upper - lower)
    elif feature.op in {"donchian_upper", "donchian_lower", "donchian_mid", "donchian_width"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        upper = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        lower = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        if feature.op == "donchian_upper":
            expr = upper
        elif feature.op == "donchian_lower":
            expr = lower
        elif feature.op == "donchian_mid":
            expr = (upper + lower) / 2.0
        else:
            expr = (upper - lower) / _safe_denominator((upper + lower) / 2.0)
    elif feature.op in {"keltner_upper", "keltner_lower", "keltner_width"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        close = pl.col(feature.columns[2])
        multiplier = feature.value if feature.value is not None else 2.0
        previous_close = close.shift(1).over("canonical_symbol")
        true_range = pl.max_horizontal(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ]
        )
        center = close.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )
        atr = true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        upper = center + (atr * multiplier)
        lower = center - (atr * multiplier)
        if feature.op == "keltner_upper":
            expr = upper
        elif feature.op == "keltner_lower":
            expr = lower
        else:
            expr = (upper - lower) / _safe_denominator(center)
    elif feature.op in {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_b"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        high_max = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        low_min = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        expr = (high_max + low_min) / 2.0
    elif feature.op == "ichimoku_span_a":
        expr = (pl.col(feature.columns[0]) + pl.col(feature.columns[1])) / 2.0
    elif feature.op == "macd_line":
        fast = first.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )
        slow_span = int(feature.value or 1)
        slow = first.ewm_mean(span=slow_span, adjust=False, min_samples=1).over("canonical_symbol")
        expr = fast - slow
    elif feature.op in {"stochastic_k", "adx"}:
        high = pl.col(feature.columns[0])
        low = pl.col(feature.columns[1])
        close = pl.col(feature.columns[2])
        if feature.op == "stochastic_k":
            low_min = low.rolling_min(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            high_max = high.rolling_max(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            expr = 100.0 * (close - low_min) / _safe_denominator(high_max - low_min)
        else:
            previous_close = close.shift(1).over("canonical_symbol")
            true_range = pl.max_horizontal(
                [
                    high - low,
                    (high - previous_close).abs(),
                    (low - previous_close).abs(),
                ]
            )
            up_move = high - high.shift(1).over("canonical_symbol")
            down_move = low.shift(1).over("canonical_symbol") - low
            plus_dm = pl.when((up_move > down_move) & (up_move > 0.0)).then(up_move).otherwise(0.0)
            minus_dm = (
                pl.when((down_move > up_move) & (down_move > 0.0)).then(down_move).otherwise(0.0)
            )
            atr = true_range.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            plus_di = (
                100.0
                * plus_dm.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                    "canonical_symbol"
                )
                / _safe_denominator(atr)
            )
            minus_di = (
                100.0
                * minus_dm.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                    "canonical_symbol"
                )
                / _safe_denominator(atr)
            )
            dx = 100.0 * (plus_di - minus_di).abs() / _safe_denominator(plus_di + minus_di)
            expr = dx.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
    elif feature.op == "stochastic_d":
        expr = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "obv":
        close = pl.col(feature.columns[0])
        volume = pl.col(feature.columns[1])
        delta = close.diff().over("canonical_symbol")
        signed_volume = pl.when(delta > 0).then(volume).when(delta < 0).then(-volume).otherwise(0.0)
        expr = signed_volume.cum_sum().over("canonical_symbol")
    elif feature.op == "volume_zscore":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        expr = (first - mean) / _safe_denominator(std)
    elif feature.op == "ts_weekday":
        expr = first.dt.weekday() - 1
    elif feature.op == "ts_hour":
        expr = first.dt.hour()
    elif feature.op == "ts_month":
        expr = first.dt.month()
    elif feature.op == "ts_day":
        expr = first.dt.day()
    elif feature.op == "pct_change":
        previous = first.shift(1).over("canonical_symbol")
        expr = (first - previous) / _safe_denominator(previous)
    elif feature.op == "log_return":
        previous = first.shift(1).over("canonical_symbol")
        expr = (first / _safe_denominator(previous)).log()
    elif feature.op == "lag":
        expr = first.shift(feature.window or 1).over("canonical_symbol")
    elif feature.op == "rolling_return":
        previous = first.shift(feature.window or 1).over("canonical_symbol")
        expr = (first / _safe_denominator(previous)) - 1.0
    elif feature.op == "ewm_mean":
        expr = first.ewm_mean(span=feature.window or 1, adjust=False, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rsi":
        delta = first.diff().over("canonical_symbol")
        gain = pl.when(delta > 0).then(delta).otherwise(0.0)
        loss = pl.when(delta < 0).then(-delta).otherwise(0.0)
        average_gain = gain.rolling_mean(
            window_size=feature.window or 1, min_samples=feature.window or 1
        ).over("canonical_symbol")
        average_loss = loss.rolling_mean(
            window_size=feature.window or 1, min_samples=feature.window or 1
        ).over("canonical_symbol")
        expr = (
            pl.when((average_loss == 0) & (average_gain > 0))
            .then(100.0)
            .when((average_loss == 0) & (average_gain == 0))
            .then(50.0)
            .otherwise(100.0 - (100.0 / (1.0 + (average_gain / average_loss))))
        )
    elif feature.op == "rolling_min":
        expr = first.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_max":
        expr = first.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_sum":
        expr = first.rolling_sum(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_mean":
        expr = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_std":
        expr = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_zscore":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        expr = (first - mean) / _safe_denominator(std)
    elif feature.op == "rolling_percentile_rank":
        expr = first.rolling_map(
            lambda values: (values <= values[-1]).sum() / len(values),
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "rolling_volatility":
        expr = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_skew":
        expr = first.rolling_skew(window_size=feature.window or 1, min_samples=3).over(
            "canonical_symbol"
        )
    elif feature.op == "rolling_kurtosis":
        expr = first.rolling_kurtosis(window_size=feature.window or 1, min_samples=4).over(
            "canonical_symbol"
        )
    elif feature.op == "annualized_volatility":
        periods = math.sqrt(feature.value if feature.value is not None else 252.0)
        expr = (
            first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            * periods
        )
    elif feature.op == "realized_variance":
        expr = (
            (first * first)
            .rolling_mean(window_size=feature.window or 1, min_samples=1)
            .over("canonical_symbol")
        )
    elif feature.op == "downside_volatility":
        downside = pl.when(first < 0.0).then(first).otherwise(0.0)
        expr = downside.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
    elif feature.op in {"sharpe_like", "sortino_like"}:
        periods = math.sqrt(feature.value if feature.value is not None else 252.0)
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        if feature.op == "sharpe_like":
            risk = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
        else:
            downside = pl.when(first < 0.0).then(first).otherwise(0.0)
            risk = downside.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
        expr = mean / _safe_denominator(risk) * periods
    elif feature.op == "kelly_fraction":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        variance = (
            first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            ** 2
        )
        expr = mean / _safe_denominator(variance)
    elif feature.op == "historical_var":
        alpha = feature.value if feature.value is not None else 0.05
        expr = -first.rolling_quantile(
            quantile=alpha,
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "expected_shortfall":
        alpha = feature.value if feature.value is not None else 0.05
        var_threshold = first.rolling_quantile(
            quantile=alpha,
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
        tail_return = pl.when(first <= var_threshold).then(first).otherwise(None)
        expr = -tail_return.rolling_mean(
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "cumulative_return":
        expr = ((1.0 + first).cum_prod().over("canonical_symbol")) - 1.0
    elif feature.op == "slope":
        previous = first.shift(feature.window or 1).over("canonical_symbol")
        expr = (first - previous) / float(feature.window or 1)
    elif feature.op == "mean_reversion_score":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        std = first.rolling_std(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        expr = -((first - mean) / _safe_denominator(std))
    elif feature.op == "distance_from_ma":
        mean = first.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        expr = (first - mean) / _safe_denominator(mean.abs())
    elif feature.op in {
        "rolling_corr",
        "rolling_beta",
        "rolling_spread_zscore",
        "tracking_error",
        "information_ratio",
    }:
        second = pl.col(feature.columns[1])
        if feature.op == "rolling_spread_zscore":
            spread = first - second
            mean = spread.rolling_mean(window_size=feature.window or 1, min_samples=1).over(
                "canonical_symbol"
            )
            std = spread.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            expr = (spread - mean) / _safe_denominator(std)
        elif feature.op in {"tracking_error", "information_ratio"}:
            active_return = first - second
            periods = feature.value if feature.value is not None else 252.0
            annualization = math.sqrt(periods)
            tracking_error = (
                active_return.rolling_std(window_size=feature.window or 1, min_samples=2).over(
                    "canonical_symbol"
                )
                * annualization
            )
            if feature.op == "tracking_error":
                expr = tracking_error
            else:
                active_mean = active_return.rolling_mean(
                    window_size=feature.window or 1, min_samples=1
                ).over("canonical_symbol")
                expr = (active_mean * periods) / _safe_denominator(tracking_error)
        else:
            mean_first = first.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            mean_second = second.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
                "canonical_symbol"
            )
            mean_product = (
                (first * second)
                .rolling_mean(window_size=feature.window or 1, min_samples=2)
                .over("canonical_symbol")
            )
            covariance = mean_product - (mean_first * mean_second)
            variance_second = (second * second).rolling_mean(
                window_size=feature.window or 1, min_samples=2
            ).over("canonical_symbol") - (mean_second * mean_second)
            if feature.op == "rolling_beta":
                expr = covariance / _safe_denominator(variance_second)
            else:
                variance_first = (first * first).rolling_mean(
                    window_size=feature.window or 1, min_samples=2
                ).over("canonical_symbol") - (mean_first * mean_first)
                expr = covariance / _safe_denominator((variance_first * variance_second).sqrt())
    elif feature.op == "rolling_autocorr":
        lagged = first.shift(1).over("canonical_symbol")
        mean_first = first.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        mean_lagged = lagged.rolling_mean(window_size=feature.window or 1, min_samples=2).over(
            "canonical_symbol"
        )
        mean_product = (
            (first * lagged)
            .rolling_mean(window_size=feature.window or 1, min_samples=2)
            .over("canonical_symbol")
        )
        covariance = mean_product - (mean_first * mean_lagged)
        variance_first = (first * first).rolling_mean(
            window_size=feature.window or 1, min_samples=2
        ).over("canonical_symbol") - (mean_first * mean_first)
        variance_lagged = (lagged * lagged).rolling_mean(
            window_size=feature.window or 1, min_samples=2
        ).over("canonical_symbol") - (mean_lagged * mean_lagged)
        expr = covariance / _safe_denominator((variance_first * variance_lagged).sqrt())
    elif feature.op == "order_flow_imbalance":
        second = pl.col(feature.columns[1])
        expr = (first - second) / _safe_denominator(first + second)
    elif feature.op == "liquidity_depth_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "spread_bps":
        ask = pl.col(feature.columns[1])
        midpoint = (first + ask) / 2.0
        expr = (ask - first) / _safe_denominator(midpoint) * 10_000.0
    elif feature.op == "funding_bps":
        expr = first * 10_000.0
    elif feature.op == "carry_adjusted_return":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "vol_risk_premium":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "put_call_skew":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "liquidity_stress":
        ask = pl.col(feature.columns[1])
        depth = pl.col(feature.columns[2])
        midpoint = (first + ask) / 2.0
        spread_bps = (ask - first) / _safe_denominator(midpoint) * 10_000.0
        expr = spread_bps / _safe_denominator(depth)
    elif feature.op == "net_exchange_flow":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "onchain_activity_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "sentiment_weighted_score":
        second = pl.col(feature.columns[1])
        expr = first * second
    elif feature.op == "event_surprise":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "fundamental_value_gap":
        second = pl.col(feature.columns[1])
        expr = (first - second) / _safe_denominator(second)
    elif feature.op == "risk_adjusted_score":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second.abs())
    elif feature.op == "inverse_volatility_weight":
        expr = 1.0 / _safe_denominator(first)
    elif feature.op == "cross_sectional_rank":
        rank = first.rank(method="ordinal", descending=True).over("ts")
        count = pl.len().over("ts")
        expr = (
            pl.when(count <= 1)
            .then(1.0)
            .otherwise(1.0 - ((rank - 1.0) / _safe_denominator(count - 1.0)))
        )
    elif feature.op in {"cross_sectional_zscore", "cross_sectional_demean"}:
        mean = first.mean().over("ts")
        demeaned = first - mean
        if feature.op == "cross_sectional_demean":
            expr = demeaned
        else:
            expr = demeaned / _safe_denominator(first.std().over("ts"))
    elif feature.op == "group_cross_sectional_rank":
        group = pl.col(feature.columns[1])
        rank = first.rank(method="ordinal", descending=True).over(["ts", group])
        count = pl.len().over(["ts", group])
        expr = (
            pl.when(count <= 1)
            .then(1.0)
            .otherwise(1.0 - ((rank - 1.0) / _safe_denominator(count - 1.0)))
        )
    elif feature.op in {"group_cross_sectional_zscore", "group_cross_sectional_demean"}:
        group = pl.col(feature.columns[1])
        mean = first.mean().over(["ts", group])
        demeaned = first - mean
        if feature.op == "group_cross_sectional_demean":
            expr = demeaned
        else:
            expr = demeaned / _safe_denominator(first.std().over(["ts", group]))
    elif feature.op == "queue_position_score":
        second = pl.col(feature.columns[1])
        expr = 1.0 - (first / _safe_denominator(first + second))
    elif feature.op == "latency_penalty_bps":
        multiplier = feature.value if feature.value is not None else 1.0
        expr = first * multiplier
    elif feature.op == "maker_taker_fee_edge_bps":
        second = pl.col(feature.columns[1])
        expr = second - first
    elif feature.op == "borrow_cost_bps":
        second = pl.col(feature.columns[1])
        expr = first * second * 10_000.0
    elif feature.op == "borrow_availability_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "tax_drag_bps":
        second = pl.col(feature.columns[1])
        expr = first * second * 10_000.0
    elif feature.op == "rebalance_drift":
        second = pl.col(feature.columns[1])
        expr = (first - second).abs()
    elif feature.op == "freshness_score":
        max_age = feature.value if feature.value is not None else 1.0
        raw = 1.0 - (first / _safe_denominator(pl.lit(max_age)))
        expr = pl.when(raw < 0.0).then(0.0).when(raw > 1.0).then(1.0).otherwise(raw)
    elif feature.op == "staleness_bps":
        multiplier = feature.value if feature.value is not None else 1.0
        expr = first * multiplier
    elif feature.op == "data_quality_blend":
        expr = pl.mean_horizontal([pl.col(column) for column in feature.columns])
    elif feature.op == "ensemble_vote_count":
        expr = pl.sum_horizontal([pl.col(column) for column in feature.columns])
    elif feature.op == "ensemble_vote_ratio":
        expr = pl.mean_horizontal([pl.col(column) for column in feature.columns])
    elif feature.op == "regime_transition_score":
        second = pl.col(feature.columns[1])
        expr = first - second
    elif feature.op == "drawdown_from_peak":
        rolling_peak = first.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        expr = (first / _safe_denominator(rolling_peak)) - 1.0
    elif feature.op == "rolling_max_drawdown":
        rolling_peak = first.rolling_max(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
        drawdown = (first / _safe_denominator(rolling_peak)) - 1.0
        expr = drawdown.rolling_min(window_size=feature.window or 1, min_samples=1).over(
            "canonical_symbol"
        )
    elif feature.op == "drawdown_duration":
        expr = first.rolling_map(
            lambda values: len(values) - 1 - int(values.arg_max() or 0),
            window_size=feature.window or 1,
            min_samples=1,
        ).over("canonical_symbol")
    elif feature.op == "turnover_pressure":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "capacity_usage_ratio":
        second = pl.col(feature.columns[1])
        expr = first / _safe_denominator(second)
    elif feature.op == "correlation_crowding_score":
        second = pl.col(feature.columns[1])
        expr = first * second
    else:
        raise StrategyAuthoringValidationError(f"Unsupported derived feature op: {feature.op}")
    if feature.fill_null is not None:
        expr = expr.fill_null(feature.fill_null)
    return expr.alias(feature.name)


def _apply_derived_features(frame: pl.DataFrame, spec: StrategyAuthoringSpec) -> pl.DataFrame:
    if not spec.rules.derived_features:
        return frame
    derived = frame.sort(["canonical_symbol", "ts"])
    for feature in spec.rules.derived_features:
        derived = derived.with_columns(_derived_expression(feature))
    return derived


def _apply_confirmation_panels(
    frame: pl.DataFrame, spec: StrategyAuthoringSpec, *, data_dir: Path
) -> pl.DataFrame:
    if not spec.data.confirmation_panels:
        return frame
    enriched = frame.sort(["canonical_symbol", "ts"])
    for panel in spec.data.confirmation_panels:
        panel_path = _resolve_path(panel.path, data_dir)
        raw_panel = pl.read_parquet(panel_path)
        if raw_panel.is_empty():
            continue
        stamp_column = f"__{panel.prefix}_ts"
        rename_map = {
            column: f"{panel.prefix}_{column}"
            for column in raw_panel.columns
            if column not in {"ts", "canonical_symbol"}
        }
        right = (
            raw_panel.with_columns(pl.col("ts").alias(stamp_column))
            .rename(rename_map)
            .sort(["canonical_symbol", "ts"])
        )
        joined = enriched.join_asof(
            right,
            on="ts",
            by="canonical_symbol",
            strategy="backward",
            check_sortedness=False,
        )
        prefixed_columns = list(rename_map.values())
        if panel.max_age_minutes is not None and prefixed_columns:
            age_minutes = (pl.col("ts") - pl.col(stamp_column)).dt.total_minutes()
            joined = joined.with_columns(
                [
                    pl.when(age_minutes <= panel.max_age_minutes)
                    .then(pl.col(column))
                    .otherwise(None)
                    .alias(column)
                    for column in prefixed_columns
                ]
            )
        enriched = joined.drop(stamp_column) if stamp_column in joined.columns else joined
    return enriched


def _entry_passes(row: dict[str, Any], entry: EntryRules) -> bool:
    all_pass = all(_condition_passes(row, condition) for condition in entry.all)
    any_pass = (
        True if not entry.any else any(_condition_passes(row, condition) for condition in entry.any)
    )
    none_pass = not any(_condition_passes(row, condition) for condition in entry.none)
    return all_pass and any_pass and none_pass


def _score(row: dict[str, Any], score: ScoreRules) -> float | None:
    if not score.enabled:
        return None
    total = 0.0
    used = False
    for term in score.weighted_sum:
        value = row.get(term.column)
        if isinstance(value, int | float):
            total += float(value) * term.weight
            used = True
    if score.model_score is not None:
        model_total = score.model_score.intercept
        model_used = False
        for term in score.model_score.coefficients:
            value = row.get(term.column)
            if not isinstance(value, int | float) and score.model_score.missing_value is not None:
                value = score.model_score.missing_value
            if isinstance(value, int | float):
                model_total += float(value) * term.weight
                model_used = True
        if model_used:
            if score.model_score.activation == "sigmoid":
                if model_total >= 0:
                    z = math.exp(-model_total)
                    model_total = 1.0 / (1.0 + z)
                else:
                    z = math.exp(model_total)
                    model_total = z / (1.0 + z)
            elif score.model_score.activation == "tanh":
                model_total = math.tanh(model_total)
            elif score.model_score.activation == "clamp_0_1":
                model_total = max(0.0, min(1.0, model_total))
            total += model_total
            used = True
    return total if used else None


def _rank_score(raw_score: float | None) -> float | None:
    if raw_score is None:
        return None
    return max(0.0, min(1.0, raw_score))


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _tail_bucket(rank_score: float | None) -> str:
    if rank_score is None:
        return "none"
    if rank_score >= 0.8:
        return "top"
    if rank_score <= 0.2:
        return "bottom"
    return "middle"


def _optional_float_from_row(row: dict[str, Any], column: str | None) -> float | None:
    if column is None:
        return None
    value = row.get(column)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return None


def _exit_bps(row: dict[str, Any], *, fixed: float | None, column: str | None) -> float | None:
    dynamic = _optional_float_from_row(row, column)
    return dynamic if dynamic is not None else fixed


def _sizing_value(row: dict[str, Any], *, fixed: float | None, column: str | None) -> float | None:
    dynamic = _optional_float_from_row(row, column)
    return dynamic if dynamic is not None else fixed


def _matching_regime_override(
    row: dict[str, Any], spec: StrategyAuthoringSpec
) -> RegimeOverride | None:
    for regime in spec.rules.regime_overrides:
        if _entry_passes(row, regime.when):
            return regime
    return None


def _regime_value(
    regime: RegimeOverride | None, field_name: str, default: float | None
) -> float | None:
    if regime is None:
        return default
    value = getattr(regime, field_name)
    return value if value is not None else default


def _signal_position_weight(row: dict[str, Any], spec: StrategyAuthoringSpec) -> float | None:
    regime = _matching_regime_override(row, spec)
    fixed = _regime_value(regime, "position_weight", spec.rules.sizing.position_weight)
    base = _sizing_value(row, fixed=fixed, column=spec.rules.sizing.position_weight_column)
    if (
        base is None
        or spec.rules.sizing.volatility_target is None
        or spec.rules.sizing.volatility_column is None
    ):
        return base
    observed = _optional_float_from_row(row, spec.rules.sizing.volatility_column)
    if observed is None or observed <= 0:
        return base
    scaled = base * spec.rules.sizing.volatility_target / observed
    cap = spec.rules.sizing.max_volatility_scaled_position_weight
    return min(scaled, cap) if cap is not None else scaled


def _signal_notional_usd(row: dict[str, Any], spec: StrategyAuthoringSpec) -> float | None:
    regime = _matching_regime_override(row, spec)
    fixed = _regime_value(regime, "notional_usd", spec.rules.sizing.notional_usd)
    return _sizing_value(row, fixed=fixed, column=spec.rules.sizing.notional_usd_column)


def _parse_event_ts(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise StrategyAuthoringValidationError(
                f"Invalid event window timestamp value: {value!r}"
            ) from exc
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _event_window_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    if not spec.rules.event_windows:
        return None
    ts_value = row.get("ts")
    if not isinstance(ts_value, datetime):
        raise StrategyAuthoringValidationError(f"Unsupported event window ts value: {ts_value!r}")
    ts_signal = ts_value if ts_value.tzinfo is not None else ts_value.replace(tzinfo=timezone.utc)
    for event_window in spec.rules.event_windows:
        event_ts = _parse_event_ts(row.get(event_window.event_ts_column))
        reason = event_window.block_reason or f"event_window_{event_window.name}"
        if event_ts is None:
            if event_window.mode == "allow":
                return f"{reason}_missing"
            continue
        start = event_ts - timedelta(minutes=event_window.before_minutes)
        end = event_ts + timedelta(minutes=event_window.after_minutes)
        in_window = start <= ts_signal <= end
        if event_window.mode == "allow" and not in_window:
            return f"{reason}_outside"
        if event_window.mode == "block" and in_window:
            return reason
    return None


def _risk_throttle_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    throttle = spec.rules.risk_throttle
    if not throttle.enabled:
        return None
    drawdown = _optional_float_from_row(row, throttle.max_drawdown_column)
    if (
        drawdown is not None
        and throttle.max_drawdown_floor is not None
        and drawdown <= throttle.max_drawdown_floor
    ):
        return "risk_throttle_max_drawdown"
    daily_loss = _optional_float_from_row(row, throttle.daily_loss_column)
    if (
        daily_loss is not None
        and throttle.daily_loss_floor is not None
        and daily_loss <= throttle.daily_loss_floor
    ):
        return "risk_throttle_daily_loss"
    loss_streak = _optional_float_from_row(row, throttle.loss_streak_column)
    if (
        loss_streak is not None
        and throttle.max_loss_streak is not None
        and loss_streak >= throttle.max_loss_streak
    ):
        return "risk_throttle_loss_streak"
    return None


def _data_guard_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    guard = spec.rules.data_guard
    if not guard.enabled:
        return None
    feature_age = _optional_float_from_row(row, guard.feature_age_column)
    if guard.max_feature_age_minutes is not None:
        if feature_age is None:
            return "data_guard_feature_age_missing"
        if feature_age > guard.max_feature_age_minutes:
            return "data_guard_feature_age_too_old"
    source_confidence = _optional_float_from_row(row, guard.source_confidence_column)
    if guard.min_source_confidence is not None:
        if source_confidence is None:
            return "data_guard_source_confidence_missing"
        if source_confidence < guard.min_source_confidence:
            return "data_guard_source_confidence_too_low"
    venue_quality = _optional_float_from_row(row, guard.venue_quality_score_column)
    if guard.min_venue_quality_score is not None:
        if venue_quality is None:
            return "data_guard_venue_quality_missing"
        if venue_quality < guard.min_venue_quality_score:
            return "data_guard_venue_quality_too_low"
    staleness_bps = _optional_float_from_row(row, guard.staleness_bps_column)
    if guard.max_staleness_bps is not None:
        if staleness_bps is None:
            return "data_guard_staleness_missing"
        if staleness_bps > guard.max_staleness_bps:
            return "data_guard_staleness_too_high"
    regime_transition = _optional_float_from_row(row, guard.regime_transition_score_column)
    if guard.max_regime_transition_score is not None:
        if regime_transition is None:
            return "data_guard_regime_transition_missing"
        if regime_transition > guard.max_regime_transition_score:
            return "data_guard_regime_transition_too_high"
    return None


def _format_condition(condition: Condition) -> str:
    target = (
        f"column:{condition.value_column}"
        if condition.value_column is not None
        else condition.value
        if condition.value is not None
        else ""
    )
    return f"{condition.column} {condition.op} {target}".rstrip()


def _side_from_column(row: dict[str, Any], column: str) -> Literal["long", "short", "none"]:
    value = str(row.get(column) or "").strip().lower()
    if value in {"buy", "bull", "long"}:
        return "long"
    if value in {"sell", "bear", "short"}:
        return "short"
    if value in {"", "hold", "none", "skip", "flat"}:
        return "none"
    raise StrategyAuthoringValidationError(f"Unsupported side value in {column}: {value}")


def _selected_side(
    row: dict[str, Any], rules: AuthoringRules
) -> tuple[Literal["long", "short", "none"] | None, str | None]:
    long_pass = _entry_passes(row, rules.long_entry) if rules.long_entry is not None else False
    short_pass = _entry_passes(row, rules.short_entry) if rules.short_entry is not None else False
    if long_pass and short_pass:
        return "none", "ambiguous_side"
    if long_pass:
        return "long", None
    if short_pass:
        return "short", None
    if rules.side_column is not None:
        if not _entry_passes(row, rules.entry):
            return None, None
        side = _side_from_column(row, rules.side_column)
        return (side, None) if side != "none" else ("none", "side_column_hold")
    if _entry_passes(row, rules.entry):
        if rules.side == "auto":
            if rules.cross_sectional.enabled:
                return "long", None
            return None, None
        return rules.side, None
    return None, None


def _compiled_signal_id(spec: StrategyAuthoringSpec, row: dict[str, Any], *, side: str) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts_signal"),
            "execution_symbol": row.get("execution_symbol"),
            "side": side,
            "reason_code": spec.rules.reason_code,
        }
    )


def _block_trade_row(
    row: dict[str, Any],
    *,
    spec: StrategyAuthoringSpec,
    block_reason: str,
) -> dict[str, Any]:
    blocked = dict(row)
    blocked["side"] = "none"
    blocked["signal_id"] = _compiled_signal_id(spec, blocked, side="none")
    blocked["confidence"] = 0.0
    blocked["stop_loss_bps"] = None
    blocked["take_profit_bps"] = None
    blocked["trailing_stop_bps"] = None
    blocked["partial_take_profit_bps"] = None
    blocked["partial_exit_fraction"] = None
    blocked["min_holding_minutes"] = None
    blocked["exit_on_opposite_signal"] = False
    blocked["bracket_type"] = "none"
    blocked["bracket_time_stop_minutes"] = None
    blocked["bracket_break_even_after_bps"] = None
    blocked["entry_order_type"] = "market"
    blocked["entry_limit_offset_bps"] = None
    blocked["entry_stop_offset_bps"] = None
    blocked["entry_timeout_minutes"] = None
    blocked["entry_time_in_force"] = "gtc"
    blocked["entry_post_only"] = False
    blocked["slippage_bps"] = 0.0
    blocked["max_fill_fraction"] = 0.0
    blocked["max_spread_bps"] = None
    blocked["min_depth_usd"] = None
    blocked["depth_column"] = None
    blocked["depth_participation_rate"] = 0.0
    blocked["max_latency_ms"] = None
    blocked["latency_ms"] = None
    blocked["min_queue_position_score"] = None
    blocked["queue_position_score"] = None
    blocked["min_borrow_availability_ratio"] = None
    blocked["borrow_availability_ratio"] = None
    blocked["max_borrow_cost_bps"] = None
    blocked["borrow_cost_bps"] = None
    blocked["position_weight"] = 0.0
    blocked["notional_usd"] = None
    blocked["_cross_sectional_group"] = row.get("_cross_sectional_group")
    blocked["_portfolio_group"] = row.get("_portfolio_group")
    blocked["_portfolio_turnover_weight"] = row.get("_portfolio_turnover_weight")
    blocked["reason_codes"] = [spec.rules.hold_reason_code]
    blocked["block_reasons"] = [*list(row.get("block_reasons") or []), block_reason]
    return blocked


def _score_value(row: dict[str, Any]) -> float | None:
    value = row.get("raw_score")
    return float(value) if isinstance(value, int | float) else None


def _signal_timestamp(row: dict[str, Any]) -> datetime:
    value = row["ts_signal"]
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise StrategyAuthoringValidationError(f"Unsupported ts_signal value: {value!r}")


def _temporal_block_reason(
    row: dict[str, Any],
    temporal: TemporalRules,
    *,
    last_signal_by_symbol: dict[str, datetime],
    count_by_symbol_day: dict[tuple[str, object], int],
) -> str | None:
    ts_signal = _signal_timestamp(row)
    if temporal.allowed_weekdays_utc is not None and ts_signal.weekday() not in set(
        temporal.allowed_weekdays_utc
    ):
        return "temporal_weekday_filter"
    if temporal.allowed_hours_utc is not None and ts_signal.hour not in set(
        temporal.allowed_hours_utc
    ):
        return "temporal_hour_filter"

    symbol = str(row["execution_symbol"])
    previous = last_signal_by_symbol.get(symbol)
    if (
        temporal.cooldown_minutes is not None
        and previous is not None
        and (ts_signal - previous).total_seconds() < temporal.cooldown_minutes * 60
    ):
        return "temporal_cooldown"

    day_key = (symbol, ts_signal.date())
    if (
        temporal.max_signals_per_symbol_per_day is not None
        and count_by_symbol_day.get(day_key, 0) >= temporal.max_signals_per_symbol_per_day
    ):
        return "temporal_symbol_daily_limit"
    return None


def _apply_temporal_selection(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if not spec.rules.temporal.enabled:
        return rows

    last_signal_by_symbol: dict[str, datetime] = {}
    count_by_symbol_day: dict[tuple[str, object], int] = {}
    selected: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"])):
        if row.get("side") == "none":
            selected.append(row)
            continue
        reason = _temporal_block_reason(
            row,
            spec.rules.temporal,
            last_signal_by_symbol=last_signal_by_symbol,
            count_by_symbol_day=count_by_symbol_day,
        )
        if reason is not None:
            selected.append(_block_trade_row(row, spec=spec, block_reason=reason))
            continue

        ts_signal = _signal_timestamp(row)
        symbol = str(row["execution_symbol"])
        last_signal_by_symbol[symbol] = ts_signal
        day_key = (symbol, ts_signal.date())
        count_by_symbol_day[day_key] = count_by_symbol_day.get(day_key, 0) + 1
        selected.append(row)
    return selected


def _apply_position_state_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    position = spec.rules.position
    if not position.enabled:
        return rows

    horizon_minutes = position.holding_horizon_minutes or spec.backtest.label_horizon_minutes
    active_by_symbol: dict[str, list[tuple[datetime, float]]] = {}
    selected: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"])):
        if row.get("side") == "none":
            selected.append(row)
            continue

        ts_signal = _signal_timestamp(row)
        symbol = str(row["execution_symbol"])
        active = [
            (end_at, weight)
            for end_at, weight in active_by_symbol.get(symbol, [])
            if end_at > ts_signal
        ]
        active_by_symbol[symbol] = active
        open_weight = sum(weight for _end_at, weight in active)
        weight = abs(_position_weight_value(row))

        if (
            position.max_open_signals_per_symbol is not None
            and len(active) >= position.max_open_signals_per_symbol
        ):
            selected.append(
                _block_trade_row(row, spec=spec, block_reason="position_open_signal_limit")
            )
            continue
        if (
            position.max_open_position_weight_per_symbol is not None
            and open_weight + weight > position.max_open_position_weight_per_symbol
        ):
            selected.append(
                _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
            )
            continue

        active.append((ts_signal + timedelta(minutes=horizon_minutes), weight))
        active_by_symbol[symbol] = active
        selected.append(row)
    return selected


def _apply_portfolio_allocation(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.allocation_method == "none":
        return rows
    target = portfolio.target_total_position_weight
    if target is None:
        return rows

    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        if portfolio.allocation_method in {
            "dollar_neutral",
            "beta_neutral",
            "group_neutral",
        }:
            selected.extend(
                _neutral_allocated_rows(
                    timestamp_rows,
                    target=target,
                    method=portfolio.allocation_method,
                )
            )
            continue
        raw_weights = _allocation_raw_weights(timestamp_rows, portfolio)
        total_raw = sum(raw_weights)
        for row, raw_weight in zip(timestamp_rows, raw_weights, strict=True):
            allocated = 0.0 if total_raw == 0.0 else target * raw_weight / total_raw
            updated = dict(row)
            updated["position_weight"] = allocated
            selected.append(updated)
    return selected


def _allocation_raw_weights(rows: list[dict[str, Any]], portfolio: PortfolioRules) -> list[float]:
    if portfolio.allocation_method == "equal_weight":
        return [1.0 for _row in rows]
    if portfolio.allocation_method == "score_proportional":
        raw_weights = [
            max(0.0, float(row["raw_score"]))
            if isinstance(row.get("raw_score"), int | float)
            else 0.0
            for row in rows
        ]
        return (
            raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]
        )
    raw_weights = [
        1.0 / float(row["_allocation_volatility"])
        if isinstance(row.get("_allocation_volatility"), int | float)
        and float(row["_allocation_volatility"]) > 0.0
        else 0.0
        for row in rows
    ]
    return raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]


def _neutral_allocated_rows(
    rows: list[dict[str, Any]], *, target: float, method: str
) -> list[dict[str, Any]]:
    if method == "group_neutral":
        group_rows: dict[str, list[dict[str, Any]]] = {}
        ungrouped: list[dict[str, Any]] = []
        for row in rows:
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_rows.setdefault(group, []).append(row)
            else:
                ungrouped.append(row)
        group_target = target / len(group_rows) if group_rows else 0.0
        allocated: list[dict[str, Any]] = []
        for grouped_rows in group_rows.values():
            allocated.extend(
                _side_neutral_allocated_rows(
                    grouped_rows,
                    long_target=group_target / 2.0,
                    short_target=group_target / 2.0,
                )
            )
        allocated.extend(_side_neutral_allocated_rows(ungrouped, long_target=0.0, short_target=0.0))
        return allocated

    long_target = target / 2.0
    short_target = target / 2.0
    if method == "beta_neutral":
        long_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "long")
        short_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "short")
        if long_beta > 0.0 and short_beta > 0.0:
            long_target = target * short_beta / (long_beta + short_beta)
            short_target = target * long_beta / (long_beta + short_beta)
    return _side_neutral_allocated_rows(rows, long_target=long_target, short_target=short_target)


def _weighted_average_abs_beta(rows: Iterable[dict[str, Any]]) -> float:
    weighted_beta = 0.0
    total_weight = 0.0
    for row in rows:
        beta = row.get("_allocation_beta")
        if not isinstance(beta, int | float):
            continue
        weight = abs(_position_weight_value(row))
        weighted_beta += abs(float(beta)) * weight
        total_weight += weight
    return 0.0 if total_weight == 0.0 else weighted_beta / total_weight


def _side_neutral_allocated_rows(
    rows: list[dict[str, Any]], *, long_target: float, short_target: float
) -> list[dict[str, Any]]:
    by_side = {
        "long": [row for row in rows if row.get("side") == "long"],
        "short": [row for row in rows if row.get("side") == "short"],
    }
    allocated: list[dict[str, Any]] = []
    for side, side_rows in by_side.items():
        side_target = long_target if side == "long" else short_target
        total_raw = sum(abs(_position_weight_value(row)) for row in side_rows)
        for row in side_rows:
            updated = dict(row)
            updated["position_weight"] = (
                0.0
                if total_raw == 0.0
                else side_target * abs(_position_weight_value(row)) / total_raw
            )
            allocated.append(updated)
    return allocated


def _position_weight_value(row: dict[str, Any]) -> float:
    value = row.get("position_weight")
    return float(value) if isinstance(value, int | float) else 1.0


def _portfolio_turnover_weight_value(row: dict[str, Any]) -> float:
    value = row.get("_portfolio_turnover_weight")
    if isinstance(value, int | float):
        return abs(float(value))
    return abs(_position_weight_value(row))


def _apply_portfolio_turnover_budget(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.max_turnover_weight_per_timestamp is None:
        return rows

    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        used_turnover = 0.0
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            turnover_weight = _portfolio_turnover_weight_value(row)
            if used_turnover + turnover_weight > portfolio.max_turnover_weight_per_timestamp:
                blocked_rows.append(
                    _block_trade_row(row, spec=spec, block_reason="portfolio_turnover_budget_limit")
                )
                continue
            used_turnover += turnover_weight
            accepted_rows.append(row)
        selected.extend([*blocked_rows, *accepted_rows])
    return selected


def _portfolio_exposure_block_reason(
    row: dict[str, Any],
    *,
    portfolio: PortfolioRules,
    total_weight: float,
    long_weight: float,
    short_weight: float,
    symbol_weights: dict[str, float],
    group_weights: dict[str, float],
) -> str | None:
    weight = abs(_position_weight_value(row))
    side = str(row.get("side") or "")
    symbol = str(row.get("execution_symbol") or "")
    group = str(row.get("_portfolio_group") or "").strip()
    if (
        portfolio.max_total_position_weight is not None
        and total_weight + weight > portfolio.max_total_position_weight
    ):
        return "portfolio_total_exposure_limit"
    if (
        side == "long"
        and portfolio.max_long_position_weight is not None
        and long_weight + weight > portfolio.max_long_position_weight
    ):
        return "portfolio_long_exposure_limit"
    if (
        side == "short"
        and portfolio.max_short_position_weight is not None
        and short_weight + weight > portfolio.max_short_position_weight
    ):
        return "portfolio_short_exposure_limit"
    if (
        portfolio.max_symbol_position_weight is not None
        and symbol_weights.get(symbol, 0.0) + weight > portfolio.max_symbol_position_weight
    ):
        return "portfolio_symbol_exposure_limit"
    if (
        portfolio.max_group_position_weight is not None
        or portfolio.max_group_abs_net_position_weight is not None
    ):
        if not group:
            return "portfolio_group_missing"
    if portfolio.max_group_position_weight is not None:
        if group_weights.get(group, 0.0) + weight > portfolio.max_group_position_weight:
            return "portfolio_group_exposure_limit"
    return None


def _apply_portfolio_exposure_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if not portfolio.exposure_limits_enabled:
        return rows
    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        total_weight = 0.0
        long_weight = 0.0
        short_weight = 0.0
        symbol_weights: dict[str, float] = {}
        group_weights: dict[str, float] = {}
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            reason = _portfolio_exposure_block_reason(
                row,
                portfolio=portfolio,
                total_weight=total_weight,
                long_weight=long_weight,
                short_weight=short_weight,
                symbol_weights=symbol_weights,
                group_weights=group_weights,
            )
            if reason is not None:
                blocked_rows.append(_block_trade_row(row, spec=spec, block_reason=reason))
                continue
            weight = abs(_position_weight_value(row))
            total_weight += weight
            if row.get("side") == "long":
                long_weight += weight
            elif row.get("side") == "short":
                short_weight += weight
            symbol = str(row.get("execution_symbol") or "")
            symbol_weights[symbol] = symbol_weights.get(symbol, 0.0) + weight
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_weights[group] = group_weights.get(group, 0.0) + weight
            accepted_rows.append(row)
        accepted_rows, net_blocked_rows = _apply_portfolio_net_exposure_limit(
            accepted_rows, portfolio=portfolio, spec=spec
        )
        accepted_rows, group_net_blocked_rows = _apply_portfolio_group_net_exposure_limit(
            accepted_rows, portfolio=portfolio, spec=spec
        )
        selected.extend([*blocked_rows, *net_blocked_rows, *group_net_blocked_rows, *accepted_rows])
    return selected


def _apply_portfolio_net_exposure_limit(
    rows: list[dict[str, Any]], *, portfolio: PortfolioRules, spec: StrategyAuthoringSpec
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if portfolio.max_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        long_weight = sum(
            abs(_position_weight_value(row)) for row in accepted if row.get("side") == "long"
        )
        short_weight = sum(
            abs(_position_weight_value(row)) for row in accepted if row.get("side") == "short"
        )
        net_weight = long_weight - short_weight
        if abs(net_weight) <= portfolio.max_abs_net_position_weight:
            return accepted, blocked

        overweight_side = "long" if net_weight > 0 else "short"
        candidates = [
            (index, row) for index, row in enumerate(accepted) if row.get("side") == overweight_side
        ]
        if not candidates:
            return accepted, blocked

        remove_index, row = min(
            candidates,
            key=lambda item: (
                item[1].get("rank_score") if item[1].get("rank_score") is not None else -1.0,
                item[0],
            ),
        )
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_net_exposure_limit")
        )
        accepted.pop(remove_index)


def _apply_portfolio_group_net_exposure_limit(
    rows: list[dict[str, Any]], *, portfolio: PortfolioRules, spec: StrategyAuthoringSpec
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if portfolio.max_group_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        group_rows: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for index, row in enumerate(accepted):
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_rows.setdefault(group, []).append((index, row))

        over_limit: tuple[str, float] | None = None
        for group, indexed_rows in group_rows.items():
            long_weight = sum(
                abs(_position_weight_value(row))
                for _index, row in indexed_rows
                if row.get("side") == "long"
            )
            short_weight = sum(
                abs(_position_weight_value(row))
                for _index, row in indexed_rows
                if row.get("side") == "short"
            )
            net_weight = long_weight - short_weight
            if abs(net_weight) > portfolio.max_group_abs_net_position_weight:
                over_limit = (group, net_weight)
                break
        if over_limit is None:
            return accepted, blocked

        group, net_weight = over_limit
        overweight_side = "long" if net_weight > 0 else "short"
        candidates = [
            (index, row)
            for index, row in enumerate(accepted)
            if row.get("side") == overweight_side
            and str(row.get("_portfolio_group") or "").strip() == group
        ]
        if not candidates:
            return accepted, blocked

        remove_index, row = min(
            candidates,
            key=lambda item: (
                item[1].get("rank_score") if item[1].get("rank_score") is not None else -1.0,
                item[0],
            ),
        )
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_group_net_exposure_limit")
        )
        accepted.pop(remove_index)


def _apply_cross_sectional_selection(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if not spec.rules.cross_sectional.enabled:
        return rows
    passthrough = [row for row in rows if row.get("side") == "none"]
    candidates_by_timestamp: dict[tuple[Any, str | None], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("side") == "none":
            continue
        group: str | None = None
        if spec.rules.cross_sectional.group_column is not None:
            group = str(row.get("_cross_sectional_group") or "").strip()
            if not group:
                passthrough.append(
                    _block_trade_row(
                        row,
                        spec=spec,
                        block_reason="cross_sectional_group_missing",
                    )
                )
                continue
        candidates_by_timestamp.setdefault((row["ts_signal"], group), []).append(row)

    selected_rows: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in candidates_by_timestamp.values():
        scored = [row for row in timestamp_rows if _score_value(row) is not None]
        unscored = [row for row in timestamp_rows if _score_value(row) is None]
        if (
            spec.rules.cross_sectional.min_candidates is not None
            and len(scored) < spec.rules.cross_sectional.min_candidates
        ):
            selected_rows.extend(
                _block_trade_row(row, spec=spec, block_reason="cross_sectional_min_candidates")
                for row in timestamp_rows
            )
            continue
        sorted_desc = sorted(scored, key=lambda item: _score_value(item) or 0.0, reverse=True)
        sorted_asc = list(reversed(sorted_desc))
        percentile_by_id: dict[str, float] = {}
        denominator = max(len(sorted_desc) - 1, 1)
        for index, row in enumerate(sorted_desc):
            percentile_by_id[str(row["signal_id"])] = (
                1.0 if len(sorted_desc) == 1 else 1.0 - (index / denominator)
            )

        top_n = _cross_sectional_selection_count(
            len(scored),
            fixed_count=spec.rules.cross_sectional.long_top_n,
            fraction=spec.rules.cross_sectional.long_top_fraction,
        )
        bottom_n = _cross_sectional_selection_count(
            len(scored),
            fixed_count=spec.rules.cross_sectional.short_bottom_n,
            fraction=spec.rules.cross_sectional.short_bottom_fraction,
        )
        unscored_ids = {str(row["signal_id"]) for row in unscored}
        top_ids = {str(row["signal_id"]) for row in sorted_desc[:top_n]}
        bottom_ids = {
            str(row["signal_id"])
            for row in sorted_asc[:bottom_n]
            if str(row["signal_id"]) not in top_ids
        }
        for row in timestamp_rows:
            row_id = str(row["signal_id"])
            if row_id in unscored_ids:
                selected_rows.append(
                    _block_trade_row(
                        row,
                        spec=spec,
                        block_reason="cross_sectional_score_missing",
                    )
                )
                continue
            updated = dict(row)
            percentile = percentile_by_id[row_id]
            updated["rank_score"] = percentile
            updated["percentile_rank"] = percentile
            updated["tail_bucket"] = _tail_bucket(percentile)
            if row_id in top_ids:
                if (
                    spec.rules.cross_sectional.min_long_score is not None
                    and (_score_value(row) or 0.0) < spec.rules.cross_sectional.min_long_score
                ):
                    selected_rows.append(
                        _block_trade_row(
                            updated,
                            spec=spec,
                            block_reason="cross_sectional_long_score_threshold",
                        )
                    )
                    continue
                updated["side"] = "long"
                updated["signal_id"] = _compiled_signal_id(spec, updated, side="long")
                updated["reason_codes"] = [
                    *list(row.get("reason_codes") or []),
                    "cross_sectional_top",
                ]
                selected_rows.append(updated)
            elif row_id in bottom_ids:
                if (
                    spec.rules.cross_sectional.max_short_score is not None
                    and (_score_value(row) or 0.0) > spec.rules.cross_sectional.max_short_score
                ):
                    selected_rows.append(
                        _block_trade_row(
                            updated,
                            spec=spec,
                            block_reason="cross_sectional_short_score_threshold",
                        )
                    )
                    continue
                updated["side"] = "short"
                updated["signal_id"] = _compiled_signal_id(spec, updated, side="short")
                updated["reason_codes"] = [
                    *list(row.get("reason_codes") or []),
                    "cross_sectional_bottom",
                ]
                selected_rows.append(updated)
            else:
                selected_rows.append(
                    _block_trade_row(
                        updated,
                        spec=spec,
                        block_reason="cross_sectional_rank_filter",
                    )
                )
    return selected_rows


def _cross_sectional_selection_count(
    candidate_count: int, *, fixed_count: int | None, fraction: float | None
) -> int:
    if fixed_count is not None:
        return fixed_count
    if fraction is None or candidate_count <= 0:
        return 0
    return max(1, math.ceil(candidate_count * fraction))


def _signal_id(
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    *,
    side: str | None = None,
) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts"),
            "execution_symbol": binding.execution_symbol,
            "side": side or spec.rules.side,
            "reason_code": spec.rules.reason_code,
        }
    )


def _resolve_leg_side(base_side: str, leg_side: str) -> Literal["long", "short"]:
    if leg_side == "long":
        return "long"
    if leg_side == "short":
        return "short"
    if leg_side == "same":
        return "short" if base_side == "short" else "long"
    return "long" if base_side == "short" else "short"


def _close_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="close"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "close",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "take_profit_bps": None,
        "trailing_stop_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "exit_on_add_signal": False,
        "add_fraction": None,
        "exit_on_rebalance_signal": False,
        "rebalance_target_fraction": None,
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.close_reason_code],
        "block_reasons": [],
    }


def _reduce_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="reduce"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "reduce",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "take_profit_bps": None,
        "trailing_stop_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.reduce_fraction,
            column=spec.rules.exit.reduce_fraction_column,
        ),
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.reduce_reason_code],
        "block_reasons": [],
    }


def _add_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="add"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "add",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "take_profit_bps": None,
        "trailing_stop_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "exit_on_add_signal": False,
        "add_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.add_fraction,
            column=spec.rules.exit.add_fraction_column,
        ),
        "exit_on_rebalance_signal": False,
        "rebalance_target_fraction": None,
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.add_reason_code],
        "block_reasons": [],
    }


def _rebalance_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="rebalance"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": "rebalance",
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": None,
        "take_profit_bps": None,
        "trailing_stop_bps": None,
        "partial_take_profit_bps": None,
        "partial_exit_fraction": None,
        "min_holding_minutes": None,
        "exit_on_opposite_signal": False,
        "exit_on_close_signal": False,
        "exit_on_reduce_signal": False,
        "reduce_fraction": None,
        "exit_on_add_signal": False,
        "add_fraction": None,
        "exit_on_rebalance_signal": False,
        "rebalance_target_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.rebalance_target_fraction,
            column=spec.rules.exit.rebalance_target_fraction_column,
        ),
        "bracket_type": "none",
        "bracket_time_stop_minutes": None,
        "bracket_break_even_after_bps": None,
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "slippage_bps": 0.0,
        "max_fill_fraction": 0.0,
        "max_spread_bps": None,
        "min_depth_usd": None,
        "depth_column": None,
        "depth_participation_rate": 0.0,
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
        "min_borrow_availability_ratio": None,
        "borrow_availability_ratio": None,
        "max_borrow_cost_bps": None,
        "borrow_cost_bps": None,
        "max_tax_drag_bps": None,
        "tax_drag_bps": None,
        "max_turnover_pressure": None,
        "turnover_pressure": None,
        "min_fee_edge_bps": None,
        "fee_edge_bps": None,
        "position_weight": 0.0,
        "notional_usd": None,
        "reason_codes": [spec.rules.rebalance_reason_code],
        "block_reasons": [],
    }


def _trade_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
    position_weight: float | None = None,
    notional_usd: float | None = None,
    reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    regime = _matching_regime_override(row, spec)
    effective_reason_codes = reason_codes or [spec.rules.reason_code]
    if regime is not None:
        effective_reason_codes = [*effective_reason_codes, f"regime:{regime.name}"]
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side=side),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": side,
        "raw_score": raw_score,
        "rank_score": rank,
        "percentile_rank": rank,
        "tail_bucket": _tail_bucket(rank),
        "confidence": spec.rules.confidence,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        "stop_loss_bps": _exit_bps(
            row,
            fixed=_regime_value(regime, "stop_loss_bps", spec.rules.exit.stop_loss_bps),
            column=spec.rules.exit.stop_loss_bps_column,
        ),
        "take_profit_bps": _exit_bps(
            row,
            fixed=_regime_value(regime, "take_profit_bps", spec.rules.exit.take_profit_bps),
            column=spec.rules.exit.take_profit_bps_column,
        ),
        "trailing_stop_bps": _exit_bps(
            row,
            fixed=_regime_value(regime, "trailing_stop_bps", spec.rules.exit.trailing_stop_bps),
            column=spec.rules.exit.trailing_stop_bps_column,
        ),
        "partial_take_profit_bps": _exit_bps(
            row,
            fixed=_regime_value(
                regime,
                "partial_take_profit_bps",
                spec.rules.exit.partial_take_profit_bps,
            ),
            column=spec.rules.exit.partial_take_profit_bps_column,
        ),
        "partial_exit_fraction": _sizing_value(
            row,
            fixed=_regime_value(
                regime,
                "partial_exit_fraction",
                spec.rules.exit.partial_exit_fraction,
            ),
            column=spec.rules.exit.partial_exit_fraction_column,
        ),
        "min_holding_minutes": spec.rules.exit.min_holding_minutes,
        "exit_on_opposite_signal": spec.rules.exit.exit_on_opposite_signal,
        "exit_on_close_signal": spec.rules.exit.exit_on_close_signal,
        "exit_on_reduce_signal": spec.rules.exit.exit_on_reduce_signal,
        "reduce_fraction": None,
        "exit_on_add_signal": spec.rules.exit.exit_on_add_signal,
        "add_fraction": None,
        "exit_on_rebalance_signal": spec.rules.exit.exit_on_rebalance_signal,
        "rebalance_target_fraction": None,
        "bracket_type": spec.rules.bracket.bracket_type if spec.rules.bracket.enabled else "none",
        "bracket_time_stop_minutes": (
            spec.rules.bracket.time_stop_minutes if spec.rules.bracket.enabled else None
        ),
        "bracket_break_even_after_bps": (
            spec.rules.bracket.break_even_after_bps if spec.rules.bracket.enabled else None
        ),
        "entry_order_type": spec.rules.order.entry_type,
        "entry_limit_offset_bps": spec.rules.order.limit_offset_bps,
        "entry_stop_offset_bps": spec.rules.order.stop_offset_bps,
        "entry_timeout_minutes": spec.rules.order.timeout_minutes,
        "entry_time_in_force": spec.rules.order.time_in_force,
        "entry_post_only": spec.rules.order.post_only,
        "slippage_bps": _regime_value(regime, "slippage_bps", spec.rules.execution.slippage_bps),
        "max_fill_fraction": _regime_value(
            regime, "max_fill_fraction", spec.rules.execution.max_fill_fraction
        ),
        "max_spread_bps": _regime_value(
            regime, "max_spread_bps", spec.rules.execution.max_spread_bps
        ),
        "min_depth_usd": _regime_value(regime, "min_depth_usd", spec.rules.execution.min_depth_usd),
        "depth_column": spec.rules.execution.depth_column,
        "depth_participation_rate": _regime_value(
            regime,
            "depth_participation_rate",
            spec.rules.execution.depth_participation_rate,
        ),
        "max_latency_ms": _regime_value(
            regime, "max_latency_ms", spec.rules.execution.max_latency_ms
        ),
        "latency_ms": _optional_float_from_row(row, spec.rules.execution.latency_column),
        "min_queue_position_score": _regime_value(
            regime,
            "min_queue_position_score",
            spec.rules.execution.min_queue_position_score,
        ),
        "queue_position_score": _optional_float_from_row(
            row, spec.rules.execution.queue_position_score_column
        ),
        "min_borrow_availability_ratio": _regime_value(
            regime,
            "min_borrow_availability_ratio",
            spec.rules.execution.min_borrow_availability_ratio,
        ),
        "borrow_availability_ratio": _optional_float_from_row(
            row, spec.rules.execution.borrow_availability_column
        ),
        "max_borrow_cost_bps": _regime_value(
            regime, "max_borrow_cost_bps", spec.rules.execution.max_borrow_cost_bps
        ),
        "borrow_cost_bps": _optional_float_from_row(row, spec.rules.execution.borrow_cost_column),
        "max_tax_drag_bps": _regime_value(
            regime, "max_tax_drag_bps", spec.rules.execution.max_tax_drag_bps
        ),
        "tax_drag_bps": _optional_float_from_row(row, spec.rules.execution.tax_drag_column),
        "max_turnover_pressure": _regime_value(
            regime, "max_turnover_pressure", spec.rules.execution.max_turnover_pressure
        ),
        "turnover_pressure": _optional_float_from_row(
            row, spec.rules.execution.turnover_pressure_column
        ),
        "min_fee_edge_bps": _regime_value(
            regime, "min_fee_edge_bps", spec.rules.execution.min_fee_edge_bps
        ),
        "fee_edge_bps": _optional_float_from_row(row, spec.rules.execution.fee_edge_column),
        "position_weight": position_weight
        if position_weight is not None
        else _signal_position_weight(row, spec),
        "notional_usd": notional_usd
        if notional_usd is not None
        else _signal_notional_usd(row, spec),
        "_cross_sectional_group": row.get(spec.rules.cross_sectional.group_column)
        if spec.rules.cross_sectional.group_column is not None
        else None,
        "_allocation_volatility": row.get(spec.rules.portfolio.allocation_volatility_column)
        if spec.rules.portfolio.allocation_volatility_column is not None
        else None,
        "_allocation_beta": row.get(spec.rules.portfolio.allocation_beta_column)
        if spec.rules.portfolio.allocation_beta_column is not None
        else None,
        "_portfolio_group": row.get(spec.rules.portfolio.group_column)
        if spec.rules.portfolio.group_column is not None
        else None,
        "_portfolio_turnover_weight": row.get(spec.rules.portfolio.turnover_weight_column)
        if spec.rules.portfolio.turnover_weight_column is not None
        else None,
        "reason_codes": effective_reason_codes,
        "block_reasons": [],
    }


def _multi_leg_signal_rows(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    bindings: dict[str, SymbolBinding],
    base_side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
) -> list[dict[str, Any]]:
    base_weight = _sizing_value(
        row,
        fixed=_signal_position_weight(row, spec),
        column=None,
    )
    base_notional = _sizing_value(
        row,
        fixed=_signal_notional_usd(row, spec),
        column=None,
    )
    rows: list[dict[str, Any]] = []
    for index, leg in enumerate(spec.rules.multi_leg.legs):
        binding = bindings[leg.real_market_symbol]
        leg_side = _resolve_leg_side(base_side, leg.side)
        leg_weight_multiplier = _sizing_value(
            row,
            fixed=leg.position_weight,
            column=leg.position_weight_column,
        )
        leg_weight = (base_weight if base_weight is not None else 1.0) * (
            leg_weight_multiplier if leg_weight_multiplier is not None else 1.0
        )
        leg_notional = _sizing_value(
            row,
            fixed=leg.notional_usd,
            column=leg.notional_usd_column,
        )
        if leg_notional is None and base_notional is not None:
            leg_notional = base_notional * (
                leg_weight_multiplier if leg_weight_multiplier is not None else leg.position_weight
            )
        rows.append(
            _trade_signal_row(
                spec=spec,
                row=row,
                binding=binding,
                side=leg_side,
                generated_at=generated_at,
                raw_score=raw_score,
                rank=rank,
                position_weight=leg_weight,
                notional_usd=leg_notional,
                reason_codes=[
                    spec.rules.reason_code,
                    "multi_leg",
                    leg.reason_code or f"leg_{index + 1}",
                ],
            )
        )
    return rows


def build_authoring_signals(
    spec: StrategyAuthoringSpec, *, data_dir: Path
) -> tuple[pl.DataFrame, StrategySignalManifest]:
    errors = validate_authoring_inputs(spec, data_dir=data_dir)
    if errors:
        raise StrategyAuthoringValidationError("; ".join(errors))
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    feature = _apply_condition_features(
        _apply_derived_features(
            _apply_confirmation_panels(pl.read_parquet(feature_path), spec, data_dir=data_dir),
            spec,
        ),
        spec,
    )
    bindings = {binding.real_market_symbol: binding for binding in spec.experiment.symbol_bindings}
    rows: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc)
    for row in feature.sort(["canonical_symbol", "ts"]).to_dicts():
        symbol = str(row.get("canonical_symbol") or "").upper()
        if (
            spec.rules.multi_leg.enabled
            and symbol != spec.rules.multi_leg.anchor_real_market_symbol
        ):
            continue
        binding = bindings.get(symbol)
        if binding is None:
            continue
        if spec.rules.close is not None and _entry_passes(row, spec.rules.close):
            rows.append(
                _close_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.reduce is not None and _entry_passes(row, spec.rules.reduce):
            rows.append(
                _reduce_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.add is not None and _entry_passes(row, spec.rules.add):
            rows.append(
                _add_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.rebalance is not None and _entry_passes(row, spec.rules.rebalance):
            rows.append(
                _rebalance_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.hold is not None and _entry_passes(row, spec.rules.hold):
            rows.append(
                {
                    "schema_version": "strategy_signal.v1",
                    "signal_id": _signal_id(spec, row, binding, side="none"),
                    "generated_at": generated_at,
                    "strategy_id": spec.experiment.strategy_id,
                    "strategy_family": spec.experiment.strategy_family,
                    "strategy_version": spec.experiment.strategy_version,
                    "trial_id": None,
                    "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
                    "ts_signal": row["ts"],
                    "timeframe": spec.rules.timeframe,
                    "execution_venue": binding.execution_venue,
                    "execution_symbol": binding.execution_symbol,
                    "real_market_symbol": binding.real_market_symbol,
                    "side": "none",
                    "raw_score": None,
                    "rank_score": None,
                    "percentile_rank": None,
                    "tail_bucket": "none",
                    "confidence": 0.0,
                    "source_confidence": row.get("source_confidence"),
                    "venue_quality_score": row.get("venue_quality_score"),
                    "feature_snapshot_ref": None,
                    "quote_ref": None,
                    "tracking_ref": None,
                    "stop_loss_bps": None,
                    "take_profit_bps": None,
                    "trailing_stop_bps": None,
                    "partial_take_profit_bps": None,
                    "partial_exit_fraction": None,
                    "min_holding_minutes": None,
                    "exit_on_opposite_signal": False,
                    "exit_on_close_signal": False,
                    "exit_on_reduce_signal": False,
                    "reduce_fraction": None,
                    "exit_on_add_signal": False,
                    "add_fraction": None,
                    "exit_on_rebalance_signal": False,
                    "rebalance_target_fraction": None,
                    "bracket_type": "none",
                    "bracket_time_stop_minutes": None,
                    "bracket_break_even_after_bps": None,
                    "entry_order_type": "market",
                    "entry_limit_offset_bps": None,
                    "entry_stop_offset_bps": None,
                    "entry_timeout_minutes": None,
                    "entry_time_in_force": "gtc",
                    "entry_post_only": False,
                    "slippage_bps": 0.0,
                    "max_fill_fraction": 0.0,
                    "max_spread_bps": None,
                    "min_depth_usd": None,
                    "depth_column": None,
                    "depth_participation_rate": 0.0,
                    "max_latency_ms": None,
                    "latency_ms": None,
                    "min_queue_position_score": None,
                    "queue_position_score": None,
                    "min_borrow_availability_ratio": None,
                    "borrow_availability_ratio": None,
                    "max_borrow_cost_bps": None,
                    "borrow_cost_bps": None,
                    "max_tax_drag_bps": None,
                    "tax_drag_bps": None,
                    "max_turnover_pressure": None,
                    "turnover_pressure": None,
                    "min_fee_edge_bps": None,
                    "fee_edge_bps": None,
                    "position_weight": 0.0,
                    "notional_usd": None,
                    "reason_codes": [spec.rules.hold_reason_code],
                    "block_reasons": ["hold_rule"],
                }
            )
            continue
        signal_side, block_reason = _selected_side(row, spec.rules)
        if signal_side is None:
            continue
        if signal_side == "none":
            rows.append(
                {
                    "schema_version": "strategy_signal.v1",
                    "signal_id": _signal_id(spec, row, binding, side="none"),
                    "generated_at": generated_at,
                    "strategy_id": spec.experiment.strategy_id,
                    "strategy_family": spec.experiment.strategy_family,
                    "strategy_version": spec.experiment.strategy_version,
                    "trial_id": None,
                    "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
                    "ts_signal": row["ts"],
                    "timeframe": spec.rules.timeframe,
                    "execution_venue": binding.execution_venue,
                    "execution_symbol": binding.execution_symbol,
                    "real_market_symbol": binding.real_market_symbol,
                    "side": "none",
                    "raw_score": None,
                    "rank_score": None,
                    "percentile_rank": None,
                    "tail_bucket": "none",
                    "confidence": 0.0,
                    "source_confidence": row.get("source_confidence"),
                    "venue_quality_score": row.get("venue_quality_score"),
                    "feature_snapshot_ref": None,
                    "quote_ref": None,
                    "tracking_ref": None,
                    "stop_loss_bps": None,
                    "take_profit_bps": None,
                    "trailing_stop_bps": None,
                    "partial_take_profit_bps": None,
                    "partial_exit_fraction": None,
                    "min_holding_minutes": None,
                    "exit_on_opposite_signal": False,
                    "exit_on_close_signal": False,
                    "exit_on_reduce_signal": False,
                    "reduce_fraction": None,
                    "exit_on_add_signal": False,
                    "add_fraction": None,
                    "exit_on_rebalance_signal": False,
                    "rebalance_target_fraction": None,
                    "bracket_type": "none",
                    "bracket_time_stop_minutes": None,
                    "bracket_break_even_after_bps": None,
                    "entry_order_type": "market",
                    "entry_limit_offset_bps": None,
                    "entry_stop_offset_bps": None,
                    "entry_timeout_minutes": None,
                    "entry_time_in_force": "gtc",
                    "entry_post_only": False,
                    "slippage_bps": 0.0,
                    "max_fill_fraction": 0.0,
                    "max_spread_bps": None,
                    "min_depth_usd": None,
                    "depth_column": None,
                    "depth_participation_rate": 0.0,
                    "max_latency_ms": None,
                    "latency_ms": None,
                    "min_queue_position_score": None,
                    "queue_position_score": None,
                    "min_borrow_availability_ratio": None,
                    "borrow_availability_ratio": None,
                    "max_borrow_cost_bps": None,
                    "borrow_cost_bps": None,
                    "max_tax_drag_bps": None,
                    "tax_drag_bps": None,
                    "max_turnover_pressure": None,
                    "turnover_pressure": None,
                    "min_fee_edge_bps": None,
                    "fee_edge_bps": None,
                    "position_weight": 0.0,
                    "notional_usd": None,
                    "reason_codes": [spec.rules.hold_reason_code],
                    "block_reasons": [block_reason or "hold_rule"],
                }
            )
            continue
        raw_score = _score(row, spec.rules.score)
        rank = _rank_score(raw_score)
        event_block_reason = _event_window_block_reason(row, spec)
        if event_block_reason is not None:
            rows.append(
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
                    block_reason=event_block_reason,
                )
            )
            continue
        data_guard_block_reason = _data_guard_block_reason(row, spec)
        if data_guard_block_reason is not None:
            rows.append(
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
                    block_reason=data_guard_block_reason,
                )
            )
            continue
        risk_throttle_block_reason = _risk_throttle_block_reason(row, spec)
        if risk_throttle_block_reason is not None:
            rows.append(
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
                    block_reason=risk_throttle_block_reason,
                )
            )
            continue
        if spec.rules.multi_leg.enabled:
            rows.extend(
                _multi_leg_signal_rows(
                    spec=spec,
                    row=row,
                    bindings=bindings,
                    base_side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
        else:
            rows.append(
                _trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
    rows = _apply_cross_sectional_selection(rows, spec)
    rows = _apply_temporal_selection(rows, spec)
    rows = _apply_position_state_limits(rows, spec)

    if spec.rules.portfolio.max_signals_per_timestamp is not None:
        grouped: dict[Any, list[dict[str, Any]]] = {}
        passthrough: list[dict[str, Any]] = []
        for item in rows:
            if item["side"] == "none":
                passthrough.append(item)
                continue
            grouped.setdefault(item["ts_signal"], []).append(item)
        limited: list[dict[str, Any]] = passthrough[:]
        limit = spec.rules.portfolio.max_signals_per_timestamp
        for timestamp_rows in grouped.values():
            limited.extend(
                sorted(
                    timestamp_rows,
                    key=lambda item: (
                        item.get("rank_score") if item.get("rank_score") is not None else -1.0
                    ),
                    reverse=True,
                )[:limit]
            )
        rows = limited
    rows = _apply_portfolio_allocation(rows, spec)
    rows = _apply_portfolio_turnover_budget(rows, spec)
    rows = _apply_portfolio_exposure_limits(rows, spec)
    rows = sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"]))

    frame = (
        empty_strategy_signal_frame()
        if not rows
        else validate_strategy_signal_frame(
            pl.DataFrame(rows), symbol_bindings=spec.experiment.symbol_bindings
        )
    )
    feature_hash = file_sha256(feature_path)
    run_id = (
        empty_signal_artifact_run_id(
            generator_id="strategy_authoring",
            strategy_id=spec.experiment.strategy_id,
            strategy_family=spec.experiment.strategy_family,
            strategy_version=spec.experiment.strategy_version,
            symbol_bindings=spec.experiment.symbol_bindings,
            feature_panel_sha256=feature_hash,
        )
        if frame.is_empty()
        else signal_artifact_run_id(frame)
    )
    manifest = StrategySignalManifest(
        schema_version="strategy_signal_manifest.v1",
        generated_at=generated_at,
        generator_id="strategy_authoring",
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        symbol_bindings=spec.experiment.symbol_bindings,
        feature_panel_sha256=feature_hash,
        signal_count=frame.height,
        signal_artifact_run_id=run_id,
        generator_parameters={
            "authoring_schema_version": spec.schema_version,
            "reason_code": spec.rules.reason_code,
        },
    )
    return frame, manifest


def write_authoring_signal_artifacts(
    frame: pl.DataFrame, manifest: StrategySignalManifest, *, data_dir: Path
) -> dict[str, Path]:
    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    legacy_out = data_dir / "research/signals.csv"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(parquet_out)
    with jsonl_out.open("w", encoding="utf-8") as handle:
        for row in frame.to_dicts():
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    _legacy_export(frame).write_csv(legacy_out)
    write_strategy_signal_manifest(manifest, strategy_signal_manifest_path(data_dir))
    return {
        "signals_parquet": parquet_out,
        "signals_jsonl": jsonl_out,
        "legacy_csv": legacy_out,
        "manifest": strategy_signal_manifest_path(data_dir),
    }


def strategy_signals_to_research_signals(frame: pl.DataFrame) -> list[ResearchSignal]:
    if frame.is_empty():
        return []
    return [
        ResearchSignal(
            ts_signal=row["ts_signal"],
            canonical_symbol=str(row["execution_symbol"]).upper(),
            side=str(row["side"]).lower(),
            timeframe=str(row["timeframe"]).lower(),
            signal_strength=row.get("raw_score"),
            stop_loss_bps=row.get("stop_loss_bps"),
            take_profit_bps=row.get("take_profit_bps"),
            trailing_stop_bps=row.get("trailing_stop_bps"),
            partial_take_profit_bps=row.get("partial_take_profit_bps"),
            partial_exit_fraction=row.get("partial_exit_fraction"),
            min_holding_minutes=row.get("min_holding_minutes"),
            exit_on_opposite_signal=bool(row.get("exit_on_opposite_signal")),
            exit_on_close_signal=bool(row.get("exit_on_close_signal")),
            exit_on_reduce_signal=bool(row.get("exit_on_reduce_signal")),
            reduce_fraction=row.get("reduce_fraction"),
            exit_on_add_signal=bool(row.get("exit_on_add_signal")),
            add_fraction=row.get("add_fraction"),
            exit_on_rebalance_signal=bool(row.get("exit_on_rebalance_signal")),
            rebalance_target_fraction=row.get("rebalance_target_fraction"),
            bracket_type=str(row.get("bracket_type") or "none"),
            bracket_time_stop_minutes=row.get("bracket_time_stop_minutes"),
            bracket_break_even_after_bps=row.get("bracket_break_even_after_bps"),
            entry_order_type=str(row.get("entry_order_type") or "market"),
            entry_limit_offset_bps=row.get("entry_limit_offset_bps"),
            entry_stop_offset_bps=row.get("entry_stop_offset_bps"),
            entry_timeout_minutes=row.get("entry_timeout_minutes"),
            entry_time_in_force=str(row.get("entry_time_in_force") or "gtc"),
            entry_post_only=bool(row.get("entry_post_only")),
            slippage_bps=row.get("slippage_bps") or 0.0,
            max_fill_fraction=row.get("max_fill_fraction") or 1.0,
            max_spread_bps=row.get("max_spread_bps"),
            min_depth_usd=row.get("min_depth_usd"),
            depth_column=row.get("depth_column"),
            depth_participation_rate=row.get("depth_participation_rate") or 1.0,
            max_latency_ms=row.get("max_latency_ms"),
            latency_ms=row.get("latency_ms"),
            min_queue_position_score=row.get("min_queue_position_score"),
            queue_position_score=row.get("queue_position_score"),
            min_borrow_availability_ratio=row.get("min_borrow_availability_ratio"),
            borrow_availability_ratio=row.get("borrow_availability_ratio"),
            max_borrow_cost_bps=row.get("max_borrow_cost_bps"),
            borrow_cost_bps=row.get("borrow_cost_bps"),
            max_tax_drag_bps=row.get("max_tax_drag_bps"),
            tax_drag_bps=row.get("tax_drag_bps"),
            max_turnover_pressure=row.get("max_turnover_pressure"),
            turnover_pressure=row.get("turnover_pressure"),
            min_fee_edge_bps=row.get("min_fee_edge_bps"),
            fee_edge_bps=row.get("fee_edge_bps"),
            position_weight=row.get("position_weight") or 1.0,
            notional_usd=row.get("notional_usd"),
        )
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower()
        in {"long", "short", "close", "reduce", "add", "rebalance"}
    ]


def explain_authoring_spec(spec: StrategyAuthoringSpec, *, data_dir: Path) -> str:
    errors = validate_authoring_inputs(spec, data_dir=data_dir)
    required_columns = sorted(_required_columns(spec))
    bindings = ", ".join(
        f"{item.real_market_symbol}->{item.execution_symbol}@{item.execution_venue}"
        for item in spec.experiment.symbol_bindings
    )
    conditions = [*spec.rules.entry.all, *spec.rules.entry.any, *spec.rules.entry.none]
    long_conditions = (
        [*spec.rules.long_entry.all, *spec.rules.long_entry.any, *spec.rules.long_entry.none]
        if spec.rules.long_entry is not None
        else []
    )
    short_conditions = (
        [*spec.rules.short_entry.all, *spec.rules.short_entry.any, *spec.rules.short_entry.none]
        if spec.rules.short_entry is not None
        else []
    )
    hold_conditions = (
        [*spec.rules.hold.all, *spec.rules.hold.any, *spec.rules.hold.none]
        if spec.rules.hold is not None
        else []
    )
    close_conditions = (
        [*spec.rules.close.all, *spec.rules.close.any, *spec.rules.close.none]
        if spec.rules.close is not None
        else []
    )
    reduce_conditions = (
        [*spec.rules.reduce.all, *spec.rules.reduce.any, *spec.rules.reduce.none]
        if spec.rules.reduce is not None
        else []
    )
    add_conditions = (
        [*spec.rules.add.all, *spec.rules.add.any, *spec.rules.add.none]
        if spec.rules.add is not None
        else []
    )
    rebalance_conditions = (
        [*spec.rules.rebalance.all, *spec.rules.rebalance.any, *spec.rules.rebalance.none]
        if spec.rules.rebalance is not None
        else []
    )
    condition_lines = "\n".join(f"- {_format_condition(condition)}" for condition in conditions)
    score_lines = (
        "\n".join(f"- {term.column} * {term.weight}" for term in spec.rules.score.weighted_sum)
        or "- no weighted_sum terms"
    )
    if spec.rules.score.model_score is not None:
        model = spec.rules.score.model_score
        model_lines = "\n".join(f"- {term.column} * {term.weight}" for term in model.coefficients)
        score_lines += (
            "\n"
            f"- model_score.type: {model.model_type}\n"
            f"- model_score.intercept: {model.intercept}\n"
            f"- model_score.activation: {model.activation}\n"
            f"- model_score.missing_value: {model.missing_value}\n"
            f"{model_lines}"
        )
    if not spec.rules.score.enabled:
        score_lines = "- no score; raw/rank score will be null"
    hold_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in hold_conditions
        )
        or "- no hold rules"
    )
    close_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in close_conditions
        )
        or "- no close rules"
    )
    reduce_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in reduce_conditions
        )
        or "- no reduce rules"
    )
    add_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in add_conditions
        )
        or "- no add rules"
    )
    rebalance_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in rebalance_conditions
        )
        or "- no rebalance rules"
    )
    long_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in long_conditions
        )
        or "- no long-specific rules"
    )
    short_lines = (
        "\n".join(
            f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
            for condition in short_conditions
        )
        or "- no short-specific rules"
    )
    multi_leg_lines = "- disabled"
    if spec.rules.multi_leg.enabled:
        multi_leg_lines = "\n".join(
            (
                f"- {leg.real_market_symbol} side={leg.side} "
                f"position_weight={leg.position_weight} "
                f"position_weight_column={leg.position_weight_column} "
                f"notional_usd={leg.notional_usd} "
                f"notional_usd_column={leg.notional_usd_column} "
                f"reason_code={leg.reason_code or f'leg_{index + 1}'}"
            )
            for index, leg in enumerate(spec.rules.multi_leg.legs)
        )
    status = "ok" if not errors else "invalid"
    error_lines = "\n".join(f"- {error}" for error in errors) or "- none"
    return (
        "# Strategy Authoring Explain\n\n"
        f"- status: {status}\n"
        f"- schema_version: {spec.schema_version}\n"
        f"- strategy_id: {spec.experiment.strategy_id}\n"
        f"- paper_only: true\n"
        f"- live_order_submitted: false\n"
        f"- symbol_bindings: {bindings}\n"
        f"- side: {spec.rules.side}\n"
        f"- side_column: {spec.rules.side_column}\n"
        f"- timeframe: {spec.rules.timeframe}\n"
        f"- feature_panel_path: {_resolve_path(spec.data.feature_panel_path, data_dir)}\n"
        f"- quote_data_path: {_resolve_path(spec.data.quote_data_path, data_dir)}\n"
        f"- cost_model_path: {_resolve_path(spec.data.cost_model_path, data_dir)}\n"
        "\n## Required Feature Columns\n\n"
        + "\n".join(f"- {column}" for column in required_columns)
        + "\n\n## Entry Conditions\n\n"
        + condition_lines
        + "\n\n## Long Entry Conditions\n\n"
        + long_lines
        + "\n\n## Short Entry Conditions\n\n"
        + short_lines
        + "\n\n## Hold Conditions\n\n"
        + hold_lines
        + "\n\n## Close Conditions\n\n"
        + close_lines
        + "\n\n## Reduce Conditions\n\n"
        + reduce_lines
        + "\n\n## Add Conditions\n\n"
        + add_lines
        + "\n\n## Rebalance Conditions\n\n"
        + rebalance_lines
        + "\n\n## Exit Rules\n\n"
        f"- stop_loss_bps: {spec.rules.exit.stop_loss_bps}\n"
        f"- exit_on_opposite_signal: {spec.rules.exit.exit_on_opposite_signal}\n"
        f"- exit_on_close_signal: {spec.rules.exit.exit_on_close_signal}\n"
        f"- exit_on_reduce_signal: {spec.rules.exit.exit_on_reduce_signal}\n"
        f"- reduce_fraction: {spec.rules.exit.reduce_fraction}\n"
        f"- reduce_fraction_column: {spec.rules.exit.reduce_fraction_column}\n"
        f"- exit_on_add_signal: {spec.rules.exit.exit_on_add_signal}\n"
        f"- add_fraction: {spec.rules.exit.add_fraction}\n"
        f"- add_fraction_column: {spec.rules.exit.add_fraction_column}\n"
        f"- exit_on_rebalance_signal: {spec.rules.exit.exit_on_rebalance_signal}\n"
        f"- rebalance_target_fraction: {spec.rules.exit.rebalance_target_fraction}\n"
        f"- rebalance_target_fraction_column: "
        f"{spec.rules.exit.rebalance_target_fraction_column}\n"
        f"- stop_loss_bps_column: {spec.rules.exit.stop_loss_bps_column}\n"
        f"- take_profit_bps: {spec.rules.exit.take_profit_bps}\n"
        f"- take_profit_bps_column: {spec.rules.exit.take_profit_bps_column}\n"
        f"- trailing_stop_bps: {spec.rules.exit.trailing_stop_bps}\n"
        f"- trailing_stop_bps_column: {spec.rules.exit.trailing_stop_bps_column}\n"
        f"- partial_take_profit_bps: {spec.rules.exit.partial_take_profit_bps}\n"
        f"- partial_take_profit_bps_column: {spec.rules.exit.partial_take_profit_bps_column}\n"
        f"- partial_exit_fraction: {spec.rules.exit.partial_exit_fraction}\n"
        f"- partial_exit_fraction_column: {spec.rules.exit.partial_exit_fraction_column}\n"
        f"- min_holding_minutes: {spec.rules.exit.min_holding_minutes}\n"
        "\n\n## Bracket / OCO\n\n"
        f"- enabled: {spec.rules.bracket.enabled}\n"
        f"- bracket_type: {spec.rules.bracket.bracket_type if spec.rules.bracket.enabled else 'none'}\n"
        f"- time_stop_minutes: {spec.rules.bracket.time_stop_minutes}\n"
        f"- break_even_after_bps: {spec.rules.bracket.break_even_after_bps}\n"
        "\n\n## Sizing\n\n"
        f"- position_weight: {spec.rules.sizing.position_weight}\n"
        f"- position_weight_column: {spec.rules.sizing.position_weight_column}\n"
        f"- notional_usd: {spec.rules.sizing.notional_usd}\n"
        f"- notional_usd_column: {spec.rules.sizing.notional_usd_column}\n"
        "\n\n## Order Simulation\n\n"
        f"- entry_type: {spec.rules.order.entry_type}\n"
        f"- limit_offset_bps: {spec.rules.order.limit_offset_bps}\n"
        f"- stop_offset_bps: {spec.rules.order.stop_offset_bps}\n"
        f"- timeout_minutes: {spec.rules.order.timeout_minutes}\n"
        f"- time_in_force: {spec.rules.order.time_in_force}\n"
        f"- post_only: {spec.rules.order.post_only}\n"
        "\n\n## Execution Quality\n\n"
        f"- slippage_bps: {spec.rules.execution.slippage_bps}\n"
        f"- max_fill_fraction: {spec.rules.execution.max_fill_fraction}\n"
        f"- max_spread_bps: {spec.rules.execution.max_spread_bps}\n"
        f"- min_depth_usd: {spec.rules.execution.min_depth_usd}\n"
        f"- depth_column: {spec.rules.execution.depth_column}\n"
        f"- depth_participation_rate: {spec.rules.execution.depth_participation_rate}\n"
        f"- max_latency_ms: {spec.rules.execution.max_latency_ms}\n"
        f"- latency_column: {spec.rules.execution.latency_column}\n"
        f"- min_queue_position_score: {spec.rules.execution.min_queue_position_score}\n"
        f"- queue_position_score_column: {spec.rules.execution.queue_position_score_column}\n"
        f"- min_borrow_availability_ratio: {spec.rules.execution.min_borrow_availability_ratio}\n"
        f"- borrow_availability_column: {spec.rules.execution.borrow_availability_column}\n"
        f"- max_borrow_cost_bps: {spec.rules.execution.max_borrow_cost_bps}\n"
        f"- borrow_cost_column: {spec.rules.execution.borrow_cost_column}\n"
        f"- max_tax_drag_bps: {spec.rules.execution.max_tax_drag_bps}\n"
        f"- tax_drag_column: {spec.rules.execution.tax_drag_column}\n"
        f"- max_turnover_pressure: {spec.rules.execution.max_turnover_pressure}\n"
        f"- turnover_pressure_column: {spec.rules.execution.turnover_pressure_column}\n"
        f"- min_fee_edge_bps: {spec.rules.execution.min_fee_edge_bps}\n"
        f"- fee_edge_column: {spec.rules.execution.fee_edge_column}\n"
        "\n\n## Portfolio\n\n"
        f"- max_signals_per_timestamp: {spec.rules.portfolio.max_signals_per_timestamp}\n"
        f"- allocation_method: {spec.rules.portfolio.allocation_method}\n"
        f"- target_total_position_weight: {spec.rules.portfolio.target_total_position_weight}\n"
        f"- allocation_volatility_column: {spec.rules.portfolio.allocation_volatility_column}\n"
        f"- allocation_beta_column: {spec.rules.portfolio.allocation_beta_column}\n"
        f"- max_turnover_weight_per_timestamp: "
        f"{spec.rules.portfolio.max_turnover_weight_per_timestamp}\n"
        f"- turnover_weight_column: {spec.rules.portfolio.turnover_weight_column}\n"
        f"- group_column: {spec.rules.portfolio.group_column}\n"
        "\n\n## Data Guard\n\n"
        f"- profile: {spec.rules.data_guard.profile}\n"
        f"- max_feature_age_minutes: {spec.rules.data_guard.max_feature_age_minutes}\n"
        f"- feature_age_column: {spec.rules.data_guard.feature_age_column}\n"
        f"- min_source_confidence: {spec.rules.data_guard.min_source_confidence}\n"
        f"- source_confidence_column: {spec.rules.data_guard.source_confidence_column}\n"
        f"- min_venue_quality_score: {spec.rules.data_guard.min_venue_quality_score}\n"
        f"- venue_quality_score_column: {spec.rules.data_guard.venue_quality_score_column}\n"
        f"- max_staleness_bps: {spec.rules.data_guard.max_staleness_bps}\n"
        f"- staleness_bps_column: {spec.rules.data_guard.staleness_bps_column}\n"
        f"- max_regime_transition_score: "
        f"{spec.rules.data_guard.max_regime_transition_score}\n"
        f"- regime_transition_score_column: "
        f"{spec.rules.data_guard.regime_transition_score_column}\n"
        "\n\n## Temporal Controls\n\n"
        f"- allowed_weekdays_utc: {spec.rules.temporal.allowed_weekdays_utc}\n"
        f"- allowed_hours_utc: {spec.rules.temporal.allowed_hours_utc}\n"
        f"- cooldown_minutes: {spec.rules.temporal.cooldown_minutes}\n"
        f"- max_signals_per_symbol_per_day: {spec.rules.temporal.max_signals_per_symbol_per_day}\n"
        "\n\n## Cross Sectional Selection\n\n"
        f"- long_top_n: {spec.rules.cross_sectional.long_top_n}\n"
        f"- short_bottom_n: {spec.rules.cross_sectional.short_bottom_n}\n"
        f"- long_top_fraction: {spec.rules.cross_sectional.long_top_fraction}\n"
        f"- short_bottom_fraction: {spec.rules.cross_sectional.short_bottom_fraction}\n"
        f"- group_column: {spec.rules.cross_sectional.group_column}\n"
        f"- min_candidates: {spec.rules.cross_sectional.min_candidates}\n"
        f"- min_long_score: {spec.rules.cross_sectional.min_long_score}\n"
        f"- max_short_score: {spec.rules.cross_sectional.max_short_score}\n"
        "\n\n## Multi-Leg\n\n"
        f"- enabled: {spec.rules.multi_leg.enabled}\n"
        f"- anchor_real_market_symbol: {spec.rules.multi_leg.anchor_real_market_symbol}\n"
        + multi_leg_lines
        + "\n\n## Score\n\n"
        + score_lines
        + "\n\n## Backtest\n\n"
        f"- split_method: {spec.backtest.split_method}\n"
        f"- era_unit: {spec.backtest.era_unit}\n"
        f"- label_horizon_minutes: {spec.backtest.label_horizon_minutes}\n"
        f"- min_trade_count: {spec.backtest.min_trade_count}\n"
        "\n## Validation Errors\n\n" + error_lines + "\n"
    )


def _metrics_json(
    metrics: list[Any], summary: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_authoring_backtest_result.v1",
        "strategy_id": spec.experiment.strategy_id,
        "paper_only": True,
        "live_order_submitted": False,
        "summary": summary,
        "metrics": [asdict(item) for item in metrics],
    }


def _increment_count(counts: dict[str, int], raw: object) -> None:
    key = str(raw)
    if not key:
        return
    counts[key] = counts.get(key, 0) + 1


def _count_values(rows: list[dict[str, Any]], column: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(column)
        if isinstance(value, list):
            for item in value:
                _increment_count(counts, item)
        elif value is not None:
            _increment_count(counts, value)
    return dict(sorted(counts.items()))


def _strategy_scorecard(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, summary: dict[str, Any]
) -> dict[str, Any]:
    rows = frame.to_dicts() if not frame.is_empty() else []
    derived_feature_ops: dict[str, int] = {}
    for feature in spec.rules.derived_features:
        derived_feature_ops[feature.op] = derived_feature_ops.get(feature.op, 0) + 1
    pass_thresholds = summary.get("pass_thresholds", {})
    failed_thresholds = [
        name
        for name, result in pass_thresholds.items()
        if isinstance(result, dict) and not bool(result.get("passed"))
    ]
    passed_thresholds = [
        name
        for name, result in pass_thresholds.items()
        if isinstance(result, dict) and bool(result.get("passed"))
    ]
    return {
        "schema_version": "strategy_authoring_scorecard.v1",
        "derived_feature_count": len(spec.rules.derived_features),
        "derived_feature_names": [feature.name for feature in spec.rules.derived_features],
        "derived_feature_ops": dict(sorted(derived_feature_ops.items())),
        "signal_count": frame.height,
        "side_counts": _count_values(rows, "side"),
        "reason_code_counts": _count_values(rows, "reason_codes"),
        "block_reason_counts": _count_values(rows, "block_reasons"),
        "execution_block_reason_counts": dict(
            sorted((summary.get("blocked_reason_counts") or {}).items())
        ),
        "exit_reason_counts": dict(sorted((summary.get("exit_reason_counts") or {}).items())),
        "passed_thresholds": sorted(passed_thresholds),
        "failed_thresholds": sorted(failed_thresholds),
        "backtest_passed": bool(summary.get("backtest_passed")),
        "paper_only": True,
        "live_order_submitted": False,
    }


def _paper_preview_scorecard_summary(summary: dict[str, Any]) -> dict[str, Any]:
    scorecard = summary.get("strategy_scorecard")
    if not isinstance(scorecard, dict):
        return {}
    keys = (
        "schema_version",
        "derived_feature_count",
        "signal_count",
        "side_counts",
        "block_reason_counts",
        "execution_block_reason_counts",
        "exit_reason_counts",
        "passed_thresholds",
        "failed_thresholds",
        "backtest_passed",
        "paper_only",
        "live_order_submitted",
    )
    return {key: scorecard[key] for key in keys if key in scorecard}


def _aggregate_backtest_metrics(metrics: list[Any]) -> dict[str, float | int | None]:
    if not metrics:
        return {
            "trade_count": 0,
            "total_return": 0.0,
            "max_drawdown": None,
            "cost_drag_bps": 0.0,
            "stale_rejected_count": 0,
            "halt_rejected_count": 0,
        }
    return {
        "trade_count": sum(item.trade_count for item in metrics),
        "total_return": sum(item.total_return for item in metrics),
        "max_drawdown": min(item.max_drawdown for item in metrics),
        "cost_drag_bps": sum(item.cost_drag_bps for item in metrics),
        "stale_rejected_count": sum(item.stale_rejected_count for item in metrics),
        "halt_rejected_count": sum(item.halt_rejected_count for item in metrics),
    }


def _aggregate_bundle_metrics(members: list[dict[str, Any]]) -> dict[str, float | int | None]:
    if not members:
        return {
            "member_count": 0,
            "trade_count": 0,
            "weighted_total_return": 0.0,
            "max_drawdown": None,
            "cost_drag_bps": 0.0,
        }
    weighted_total_return = 0.0
    max_drawdowns: list[float] = []
    trade_count = 0
    cost_drag_bps = 0.0
    for member in members:
        weight = float(member["effective_allocation_weight"])
        metrics = member["summary"]["aggregate_metrics"]
        weighted_total_return += float(metrics.get("total_return") or 0.0) * weight
        if metrics.get("max_drawdown") is not None:
            max_drawdowns.append(float(metrics["max_drawdown"]) * weight)
        trade_count += int(metrics.get("trade_count") or 0)
        cost_drag_bps += float(metrics.get("cost_drag_bps") or 0.0) * weight
    return {
        "member_count": len(members),
        "trade_count": trade_count,
        "weighted_total_return": weighted_total_return,
        "max_drawdown": min(max_drawdowns) if max_drawdowns else None,
        "cost_drag_bps": cost_drag_bps,
    }


def _cap_bundle_weights(
    raw_weights: dict[int, float], max_total_allocation_weight: float | None
) -> dict[int, float]:
    total = sum(raw_weights.values())
    if total <= 0:
        return {index: 0.0 for index in raw_weights}
    scale = (
        min(1.0, max_total_allocation_weight / total)
        if max_total_allocation_weight is not None
        else 1.0
    )
    return {index: weight * scale for index, weight in raw_weights.items()}


def _risk_parity_risk_value(member: dict[str, Any]) -> float:
    metrics = member["summary"]["aggregate_metrics"]
    drawdown = metrics.get("max_drawdown")
    if drawdown is None:
        return 1.0
    return max(abs(float(drawdown)), 0.0001)


def _bundle_effective_weights(
    bundle: StrategyAuthoringBundleSpec, member_results: list[dict[str, Any]]
) -> dict[int, float]:
    if not member_results:
        return {}
    if bundle.portfolio.allocation_method == "equal_weight":
        raw = {int(member["member_index"]): 1.0 / len(member_results) for member in member_results}
    elif bundle.portfolio.allocation_method == "risk_parity":
        inverse_risk = {
            int(member["member_index"]): 1.0 / _risk_parity_risk_value(member)
            for member in member_results
        }
        total_inverse = sum(inverse_risk.values())
        raw = {
            index: (weight / total_inverse if total_inverse > 0 else 0.0)
            for index, weight in inverse_risk.items()
        }
    else:
        raw = {
            index: member.allocation_weight
            for index, member in enumerate(bundle.members)
            if member.enabled
        }
    return _cap_bundle_weights(raw, bundle.portfolio.max_total_allocation_weight)


def _threshold_passes(metric_name: str, actual: float | int | None, threshold: float) -> bool:
    if actual is None:
        return False
    if metric_name in {"cost_drag_bps", "stale_rejected_count", "halt_rejected_count"}:
        return float(actual) <= threshold
    return float(actual) >= threshold


def _evaluate_pass_thresholds(
    spec: StrategyAuthoringSpec, aggregate_metrics: dict[str, float | int | None]
) -> dict[str, dict[str, float | int | bool | None]]:
    results: dict[str, dict[str, float | int | bool | None]] = {}
    for metric_name, threshold in spec.backtest.pass_thresholds.items():
        actual = aggregate_metrics.get(metric_name)
        results[metric_name] = {
            "actual": actual,
            "threshold": threshold,
            "passed": _threshold_passes(metric_name, actual, threshold),
        }
    return results


def _era_key(value: object, era_unit: str) -> str:
    ts = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if era_unit == "month":
        return ts.strftime("%Y-%m")
    if era_unit == "week":
        year, week, _weekday = ts.isocalendar()
        return f"{year}-W{week:02d}"
    return ts.strftime("%Y-%m-%d")


def _walk_forward_eras(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, *, data_dir: Path
) -> list[dict[str, Any]]:
    if frame.is_empty():
        return []
    eras: list[dict[str, Any]] = []
    for era in sorted(
        {_era_key(row["ts_signal"], spec.backtest.era_unit) for row in frame.to_dicts()}
    ):
        era_frame = frame.filter(
            pl.col("ts_signal").map_elements(
                lambda value: _era_key(value, spec.backtest.era_unit) == era,
                return_dtype=pl.Boolean,
            )
        )
        metrics, summary = _run_authoring_backtest_once(spec, era_frame, data_dir=data_dir)
        eras.append(
            {
                "era": era,
                "signal_count": era_frame.height,
                "aggregate_metrics": _aggregate_backtest_metrics(metrics),
                "executed_count": summary.get("executed_count", 0),
            }
        )
    return eras


def _set_path(payload: dict[str, Any], dotted_path: str, value: float | int | str) -> None:
    current: dict[str, Any] = payload
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        next_item = current.setdefault(part, {})
        if not isinstance(next_item, dict):
            raise StrategyAuthoringValidationError(f"Cannot set optimizer path: {dotted_path}")
        current = next_item
    current[parts[-1]] = value


def _nested_get(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _optimizer_sort_value(item: dict[str, Any], metric_name: str, *, maximize: bool) -> float:
    value = item["aggregate_metrics"].get(metric_name)
    if value is None:
        return float("-inf") if maximize else float("inf")
    return float(value)


def _optimizer_variants(spec: StrategyAuthoringSpec) -> list[tuple[str, StrategyAuthoringSpec]]:
    sweep = spec.optimizer.parameter_sweep
    if not sweep:
        return []
    paths = sorted(sweep)
    combinations = list(product(*(sweep[path] for path in paths)))
    if len(combinations) > spec.optimizer.max_variants:
        raise StrategyAuthoringValidationError(
            f"optimizer variants exceed max_variants: {len(combinations)} > {spec.optimizer.max_variants}"
        )
    variants: list[tuple[str, StrategyAuthoringSpec]] = []
    base_payload = spec.model_dump(mode="json")
    for index, values in enumerate(combinations):
        payload = json.loads(json.dumps(base_payload))
        payload["optimizer"]["parameter_sweep"] = {}
        parameters = dict(zip(paths, values, strict=True))
        for path, value in parameters.items():
            _set_path(payload, path, value)
        variant = StrategyAuthoringSpec.model_validate(payload)
        variants.append((f"variant-{index:03d}-{_stable_digest(parameters)}", variant))
    return variants


def _run_authoring_backtest_once(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, *, data_dir: Path
) -> tuple[list[Any], dict[str, Any]]:
    quote_path = _resolve_path(spec.data.quote_data_path, data_dir)
    cost_path = _resolve_path(spec.data.cost_model_path, data_dir)
    signals = strategy_signals_to_research_signals(frame)
    metrics, _records, summary = run_backtest_bridge_for_signals(
        quote_path,
        signals,
        cost_matrix_path=cost_path if cost_path.exists() else None,
        exit_model="fixed_horizon",
        holding_horizon_minutes=spec.backtest.label_horizon_minutes,
    )
    aggregate_metrics = _aggregate_backtest_metrics(metrics)
    threshold_results = _evaluate_pass_thresholds(spec, aggregate_metrics)
    pass_all_thresholds = all(bool(result["passed"]) for result in threshold_results.values())
    summary["authoring_split_method"] = spec.backtest.split_method
    summary["authoring_era_unit"] = spec.backtest.era_unit
    summary["min_trade_count"] = spec.backtest.min_trade_count
    summary["aggregate_metrics"] = aggregate_metrics
    summary["pass_thresholds"] = threshold_results
    summary["pass_all_thresholds"] = pass_all_thresholds
    summary["pass_min_trade_count"] = (
        aggregate_metrics["trade_count"] or 0
    ) >= spec.backtest.min_trade_count
    summary["backtest_passed"] = summary["pass_min_trade_count"] and pass_all_thresholds
    return metrics, summary


def run_authoring_backtest(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, *, data_dir: Path
) -> tuple[list[Any], dict[str, Any]]:
    metrics, summary = _run_authoring_backtest_once(spec, frame, data_dir=data_dir)
    if spec.backtest.split_method in {"walk_forward", "purged_walk_forward"}:
        summary["walk_forward_eras"] = _walk_forward_eras(spec, frame, data_dir=data_dir)
    variant_results = []
    for variant_id, variant in _optimizer_variants(spec):
        variant_frame, _manifest = build_authoring_signals(variant, data_dir=data_dir)
        _variant_metrics, variant_summary = _run_authoring_backtest_once(
            variant, variant_frame, data_dir=data_dir
        )
        variant_results.append(
            {
                "variant_id": variant_id,
                "parameters": {
                    path: _nested_get(variant.model_dump(mode="json"), path)
                    for path in sorted(spec.optimizer.parameter_sweep)
                },
                "aggregate_metrics": variant_summary["aggregate_metrics"],
                "backtest_passed": variant_summary["backtest_passed"],
            }
        )
    if variant_results:
        metric_name = spec.optimizer.selection_metric
        reverse = spec.optimizer.selection_direction == "maximize"
        ranked = sorted(
            variant_results,
            key=lambda item: _optimizer_sort_value(item, metric_name, maximize=reverse),
            reverse=reverse,
        )
        summary["optimizer"] = {
            "selection_metric": metric_name,
            "selection_direction": spec.optimizer.selection_direction,
            "variant_count": len(variant_results),
            "best_variant": ranked[0],
            "variants": ranked,
        }
    summary["strategy_scorecard"] = _strategy_scorecard(spec, frame, summary)
    return metrics, summary


def write_authoring_backtest_outputs(
    spec: StrategyAuthoringSpec, metrics: list[Any], summary: dict[str, Any], *, data_dir: Path
) -> dict[str, Path]:
    metrics_path = data_dir / "research/strategy_backtest_metrics.json"
    report_path = data_dir / "reports/strategy_backtest_report.md"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _metrics_json(metrics, summary, spec)
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    rows = "\n".join(
        f"| {item.venue} | {item.canonical_symbol} | {item.trade_count} | {item.total_return:.6f} | {item.max_drawdown:.6f} | {item.cost_drag_bps:.2f} |"
        for item in metrics
    )
    scorecard = summary.get("strategy_scorecard") or {}
    scorecard_lines = (
        "\n".join(
            f"- {name}: {count}"
            for name, count in (scorecard.get("derived_feature_ops") or {}).items()
        )
        or "- none"
    )
    block_reason_lines = (
        "\n".join(
            f"- {name}: {count}"
            for name, count in (scorecard.get("block_reason_counts") or {}).items()
        )
        or "- none"
    )
    report_path.write_text(
        "# Strategy Authoring Backtest Report\n\n"
        "paper_only: true\n\n"
        f"- strategy_id: {spec.experiment.strategy_id}\n"
        f"- signals_considered: {summary.get('signals_considered')}\n"
        f"- executed_count: {summary.get('executed_count')}\n"
        f"- pass_min_trade_count: {summary.get('pass_min_trade_count')}\n\n"
        f"- pass_all_thresholds: {summary.get('pass_all_thresholds')}\n"
        f"- backtest_passed: {summary.get('backtest_passed')}\n\n"
        "## Strategy Scorecard\n\n"
        f"- derived_feature_count: {scorecard.get('derived_feature_count', 0)}\n"
        f"- failed_thresholds: {scorecard.get('failed_thresholds', [])}\n\n"
        "### Derived Feature Ops\n\n"
        f"{scorecard_lines}\n\n"
        "### Signal Block Reasons\n\n"
        f"{block_reason_lines}\n\n"
        "| Venue | Symbol | Trades | Total Return | Max Drawdown | Cost Drag bps |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    return {"metrics": metrics_path, "report": report_path}


def _resolve_member_spec_path(raw: str, bundle_path: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else bundle_path.parent / path


def run_authoring_bundle(
    bundle: StrategyAuthoringBundleSpec, *, bundle_path: Path, data_dir: Path
) -> dict[str, Any]:
    member_results: list[dict[str, Any]] = []
    for index, member in enumerate(bundle.members):
        if not member.enabled:
            continue
        spec_path = _resolve_member_spec_path(member.spec_path, bundle_path)
        spec = load_authoring_spec(spec_path)
        frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)
        _metrics, summary = run_authoring_backtest(spec, frame, data_dir=data_dir)
        member_results.append(
            {
                "member_index": index,
                "spec_path": str(spec_path),
                "strategy_id": spec.experiment.strategy_id,
                "allocation_weight": member.allocation_weight,
                "effective_allocation_weight": 0.0,
                "signal_count": frame.height,
                "summary": summary,
            }
        )
    effective_weights = _bundle_effective_weights(bundle, member_results)
    for member_result in member_results:
        member_result["effective_allocation_weight"] = effective_weights.get(
            int(member_result["member_index"]), 0.0
        )
    aggregate_metrics = _aggregate_bundle_metrics(member_results)
    metric_name = bundle.portfolio.selection_metric
    reverse = bundle.portfolio.selection_direction == "maximize"
    ranked_members = sorted(
        member_results,
        key=lambda item: _optimizer_sort_value(
            {"aggregate_metrics": item["summary"]["aggregate_metrics"]},
            metric_name,
            maximize=reverse,
        ),
        reverse=reverse,
    )
    return {
        "schema_version": "strategy_authoring_bundle_result.v1",
        "bundle_id": bundle.bundle_id,
        "paper_only": True,
        "live_order_submitted": False,
        "portfolio": bundle.portfolio.model_dump(mode="json"),
        "aggregate_metrics": aggregate_metrics,
        "best_member": ranked_members[0] if ranked_members else None,
        "members": ranked_members,
    }


def write_authoring_bundle_outputs(payload: dict[str, Any], *, data_dir: Path) -> dict[str, Path]:
    result_path = data_dir / "research/strategy_authoring_bundle_result.json"
    report_path = data_dir / "reports/strategy_authoring_bundle_report.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    rows = "\n".join(
        "| {strategy_id} | {weight:.4f} | {trades} | {total_return:.6f} | {passed} |".format(
            strategy_id=member["strategy_id"],
            weight=float(member["effective_allocation_weight"]),
            trades=member["summary"]["aggregate_metrics"].get("trade_count") or 0,
            total_return=float(member["summary"]["aggregate_metrics"].get("total_return") or 0.0),
            passed=member["summary"].get("backtest_passed"),
        )
        for member in payload["members"]
    )
    report_path.write_text(
        "# Strategy Authoring Bundle Report\n\n"
        "paper_only: true\n\n"
        f"- bundle_id: {payload['bundle_id']}\n"
        f"- member_count: {payload['aggregate_metrics']['member_count']}\n"
        f"- weighted_total_return: {payload['aggregate_metrics']['weighted_total_return']:.6f}\n"
        f"- best_member: {(payload.get('best_member') or {}).get('strategy_id')}\n\n"
        "| Strategy | Effective Weight | Trades | Total Return | Backtest Passed |\n"
        "|---|---:|---:|---:|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    return {"bundle_result": result_path, "bundle_report": report_path}


def write_authoring_paper_preview_outputs(
    spec: StrategyAuthoringSpec,
    frame: pl.DataFrame,
    summary: dict[str, Any],
    *,
    data_dir: Path,
) -> dict[str, Path]:
    now = datetime.now(timezone.utc)
    parameter_hash = _stable_digest(spec.model_dump(mode="json"))
    run_id = signal_artifact_run_id(frame) if not frame.is_empty() else parameter_hash
    trial_id = f"trial-{run_id}"
    trial_group_id = f"trial-group-{run_id}"
    scorecard_summary = _paper_preview_scorecard_summary(summary)
    selected_rows = [
        row
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower() in {"long", "short"}
        and not list(row.get("block_reasons") or [])
    ][:1]
    selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
    selected = bool(selected_signal_ids) and bool(summary.get("backtest_passed", False))
    record = TrialRecord(
        schema_version="trial_record.v1",
        trial_id=trial_id,
        trial_group_id=trial_group_id,
        trial_index=0,
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        parameter_hash=parameter_hash,
        parameter_count=1,
        parameter_space_hash="strategy-authoring-yaml-v1",
        random_seed=None,
        git_sha=None,
        signal_count=frame.height,
        candidate_count=frame.height,
        paper_candidate_count=len(selected_signal_ids) if selected else 0,
        executed_count=0,
        blocked_count=0 if selected else 1,
        no_signal_count=0 if selected_signal_ids else 1,
        blocked_reason_counts={} if selected else {"not_selected": 1},
        metrics={**summary, "selected_signal_ids": selected_signal_ids if selected else []},
        baseline_strategy_id=None,
        baseline_delta_metrics={},
        selected_for_next_stage=selected,
        rejection_reasons=[] if selected else ["insufficient_trades_or_no_signal"],
    )
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    ledger = TrialLedger(ledger_path)
    existing_ids = {item.trial_id for item in ledger.read_all()}
    if record.trial_id not in existing_ids:
        ledger.append(record)

    candidates: list[TradeCandidate] = []
    selected_candidate_ids: list[str] = []
    rejected_candidate_ids: list[str] = []
    rows_for_candidates = selected_rows if selected_rows else [{}]
    for row in rows_for_candidates:
        candidate_id = (
            f"candidate-{trial_id}-{row['signal_id']}" if row else f"candidate-{trial_id}-no-signal"
        )
        status = "candidate" if selected else ("no_signal" if not row else "hold")
        binding = spec.experiment.symbol_bindings[0]
        execution_venue = cast(
            Literal["trade_xyz"], row.get("execution_venue") if row else binding.execution_venue
        )
        side = cast(
            Literal["long", "short", "none"], row.get("side") if selected and row else "none"
        )
        entry_order_type = cast(
            Literal["market", "limit", "stop_market"],
            row.get("entry_order_type") if selected and row else "market",
        )
        tail_bucket = cast(
            Literal["top", "middle", "bottom", "none"],
            row.get("tail_bucket") if selected and row else "none",
        )
        confidence = _float_or_default(row.get("confidence") if selected and row else None, 0.0)
        candidate = TradeCandidate(
            schema_version="trade_candidate.v1",
            candidate_id=candidate_id,
            generated_at=now,
            signal_id=str(row.get("signal_id")) if row else None,
            strategy_id=spec.experiment.strategy_id,
            trial_id=trial_id,
            execution_venue=execution_venue,
            execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
            real_market_symbol=str(row.get("real_market_symbol") or binding.real_market_symbol),
            side=side,
            timeframe=str(row.get("timeframe") or spec.rules.timeframe),
            status=status,
            raw_score=row.get("raw_score") if row else None,
            rank_score=row.get("rank_score") if selected and row else None,
            percentile_rank=row.get("percentile_rank") if selected and row else None,
            tail_bucket=tail_bucket,
            confidence=confidence,
            entry_reason_codes=list(row.get("reason_codes") or []) if selected and row else [],
            block_reasons=[] if selected else record.rejection_reasons,
            stop_loss_bps=row.get("stop_loss_bps") if selected and row else None,
            take_profit_bps=row.get("take_profit_bps") if selected and row else None,
            trailing_stop_bps=row.get("trailing_stop_bps") if selected and row else None,
            partial_take_profit_bps=(
                row.get("partial_take_profit_bps") if selected and row else None
            ),
            partial_exit_fraction=row.get("partial_exit_fraction") if selected and row else None,
            min_holding_minutes=row.get("min_holding_minutes") if selected and row else None,
            exit_on_opposite_signal=(
                bool(row.get("exit_on_opposite_signal")) if selected and row else False
            ),
            bracket_type=cast(
                Literal["none", "oco"], row.get("bracket_type") if selected and row else "none"
            ),
            bracket_time_stop_minutes=(
                row.get("bracket_time_stop_minutes") if selected and row else None
            ),
            bracket_break_even_after_bps=(
                row.get("bracket_break_even_after_bps") if selected and row else None
            ),
            entry_order_type=entry_order_type,
            entry_limit_offset_bps=row.get("entry_limit_offset_bps") if selected and row else None,
            entry_stop_offset_bps=row.get("entry_stop_offset_bps") if selected and row else None,
            entry_timeout_minutes=row.get("entry_timeout_minutes") if selected and row else None,
            entry_time_in_force=(
                cast(
                    Literal["gtc", "gtd", "ioc", "fok"],
                    row.get("entry_time_in_force") if selected and row else "gtc",
                )
            ),
            entry_post_only=bool(row.get("entry_post_only")) if selected and row else False,
            slippage_bps=_float_or_default(
                row.get("slippage_bps") if selected and row else None,
                0.0,
            ),
            max_fill_fraction=_float_or_default(
                row.get("max_fill_fraction") if selected and row else None,
                0.0,
            ),
            max_spread_bps=row.get("max_spread_bps") if selected and row else None,
            min_depth_usd=row.get("min_depth_usd") if selected and row else None,
            depth_column=row.get("depth_column") if selected and row else None,
            depth_participation_rate=_float_or_default(
                row.get("depth_participation_rate") if selected and row else None,
                0.0,
            ),
            max_latency_ms=row.get("max_latency_ms") if selected and row else None,
            latency_ms=row.get("latency_ms") if selected and row else None,
            min_queue_position_score=(
                row.get("min_queue_position_score") if selected and row else None
            ),
            queue_position_score=row.get("queue_position_score") if selected and row else None,
            min_borrow_availability_ratio=(
                row.get("min_borrow_availability_ratio") if selected and row else None
            ),
            borrow_availability_ratio=(
                row.get("borrow_availability_ratio") if selected and row else None
            ),
            max_borrow_cost_bps=row.get("max_borrow_cost_bps") if selected and row else None,
            borrow_cost_bps=row.get("borrow_cost_bps") if selected and row else None,
            max_tax_drag_bps=row.get("max_tax_drag_bps") if selected and row else None,
            tax_drag_bps=row.get("tax_drag_bps") if selected and row else None,
            max_turnover_pressure=(row.get("max_turnover_pressure") if selected and row else None),
            turnover_pressure=row.get("turnover_pressure") if selected and row else None,
            min_fee_edge_bps=row.get("min_fee_edge_bps") if selected and row else None,
            fee_edge_bps=row.get("fee_edge_bps") if selected and row else None,
            position_weight=row.get("position_weight") if selected and row else None,
            notional_usd=row.get("notional_usd") if selected and row else None,
            feature_snapshot_ref=row.get("feature_snapshot_ref") if row else None,
            quote_ref=row.get("quote_ref") if row else None,
            tracking_ref=row.get("tracking_ref") if row else None,
        )
        candidates.append(candidate)
        (selected_candidate_ids if selected else rejected_candidate_ids).append(candidate_id)

    pack = PaperCandidatePack(
        schema_version="paper_candidate_pack.v1",
        pack_id=f"paper-pack-{run_id}",
        generated_at=now,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        trial_group_id=trial_group_id,
        candidates=candidates,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        selection_policy={
            "source": "strategy_authoring",
            "default_decision": spec.promotion.default_decision,
        },
        reason_codes=["strategy_authoring_v1"],
        block_reasons=[] if selected else record.rejection_reasons,
    )
    pack_path = data_dir / "research/paper_candidate_pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")

    decision = PromotionDecision(
        schema_version="promotion_decision.v1",
        promotion_id=f"promotion-{run_id}",
        generated_at=now,
        source_pack_id=pack.pack_id,
        reviewer=None,
        from_stage="strategy_lab",
        to_stage="paper_observation",
        decision=spec.promotion.default_decision,
        required_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        observed_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        approval_reasons=[],
        rejection_reasons=["operator_review_required"],
        scorecard_summary=scorecard_summary,
    )
    decision_path = data_dir / "research/promotion_decision.json"
    decision_path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    intents: list[PaperIntentPreview] = []
    preview_path = data_dir / "bot/paper_intent_preview.json"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        json.dumps([intent.model_dump(mode="json") for intent in intents], indent=2),
        encoding="utf-8",
    )
    report_path = data_dir / "reports/paper_intent_preview.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Paper Intent Preview\n\n"
        "- source: strategy_authoring\n"
        f"- decision: {decision.decision}\n"
        f"- intents: {len(intents)}\n"
        f"- scorecard_schema_version: {scorecard_summary.get('schema_version')}\n"
        f"- scorecard_failed_thresholds: {scorecard_summary.get('failed_thresholds', [])}\n"
        "- paper_only: true\n",
        encoding="utf-8",
    )
    return {
        "trial_ledger": ledger_path,
        "paper_candidate_pack": pack_path,
        "promotion_decision": decision_path,
        "paper_intent_preview": preview_path,
        "paper_intent_preview_report": report_path,
    }


def write_authoring_run_summary(
    spec: StrategyAuthoringSpec,
    *,
    data_dir: Path,
    through: str,
    artifacts: dict[str, Path],
    signal_count: int,
) -> Path:
    out = data_dir / "research/strategy_authoring_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_run.v1",
                "strategy_id": spec.experiment.strategy_id,
                "through": through,
                "signal_count": signal_count,
                "paper_only": True,
                "live_order_submitted": False,
                "artifacts": {key: str(value) for key, value in artifacts.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out
