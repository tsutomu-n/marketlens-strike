from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sis.research.strategy_lab.authoring.contracts.core import (
    AuthoringData,
    AuthoringExperiment,
    EntryRules,
    ScoreRules,
)
from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature
from sis.research.strategy_lab.authoring.contracts.multi_leg import MultiLegRules, RegimeOverride
from sis.research.strategy_lab.authoring.contracts.risk_controls import (
    CrossSectionalRules,
    DataGuardRules,
    EventWindowRule,
    PortfolioRules,
    PositionRules,
    RiskThrottleRules,
    TemporalRules,
)
from sis.research.strategy_lab.authoring.contracts.trade_controls import (
    BracketRules,
    ExecutionRules,
    ExitRules,
    OrderRules,
    SizingRules,
)


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
    model_config = ConfigDict(extra="forbid")

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
    initial_capital_usd: float = Field(default=10000.0, ge=100.0, le=50000.0)
    evaluation_start_at: datetime | None = None
    evaluation_end_at: datetime | None = None

    @field_validator("initial_capital_usd", mode="before")
    @classmethod
    def validate_initial_capital_type(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("backtest.initial_capital_usd must be a number")
        return value

    @field_validator("evaluation_start_at", "evaluation_end_at")
    @classmethod
    def validate_evaluation_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("backtest evaluation datetimes must include timezone")
        return value

    @model_validator(mode="after")
    def validate_backtest(self) -> AuthoringBacktest:
        if self.label_horizon_minutes <= 0:
            raise ValueError("backtest.label_horizon_minutes must be positive")
        if self.purge_minutes < 0 or self.embargo_minutes < 0:
            raise ValueError("backtest purge/embargo minutes must be >= 0")
        if self.min_trade_count < 0:
            raise ValueError("backtest.min_trade_count must be >= 0")
        if (
            self.evaluation_start_at is None
            and self.evaluation_end_at is not None
            or self.evaluation_start_at is not None
            and self.evaluation_end_at is None
        ):
            raise ValueError(
                "backtest.evaluation_start_at and evaluation_end_at must be set together"
            )
        if (
            self.evaluation_start_at is not None
            and self.evaluation_end_at is not None
            and self.evaluation_start_at >= self.evaluation_end_at
        ):
            raise ValueError("backtest.evaluation_start_at must be before evaluation_end_at")
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


class BacktestSuiteBacktestOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    split_method: Literal["single_window", "walk_forward", "purged_walk_forward"] | None = None
    era_unit: Literal["trading_day", "week", "month"] | None = None
    label_horizon_minutes: int | None = None
    purge_minutes: int | None = None
    embargo_minutes: int | None = None
    min_trade_count: int | None = None
    primary_metric: str | None = None
    pass_thresholds: dict[str, float] | None = None
    initial_capital_usd: float | None = Field(default=None, ge=100.0, le=50000.0)
    evaluation_start_at: datetime | None = None
    evaluation_end_at: datetime | None = None

    @field_validator("initial_capital_usd", mode="before")
    @classmethod
    def validate_initial_capital_type(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("case.backtest.initial_capital_usd must be a number")
        return value

    @field_validator("evaluation_start_at", "evaluation_end_at")
    @classmethod
    def validate_evaluation_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("case.backtest evaluation datetimes must include timezone")
        return value

    @model_validator(mode="after")
    def validate_overrides(self) -> BacktestSuiteBacktestOverrides:
        if self.label_horizon_minutes is not None and self.label_horizon_minutes <= 0:
            raise ValueError("case.backtest.label_horizon_minutes must be positive")
        if self.purge_minutes is not None and self.purge_minutes < 0:
            raise ValueError("case.backtest.purge_minutes must be >= 0")
        if self.embargo_minutes is not None and self.embargo_minutes < 0:
            raise ValueError("case.backtest.embargo_minutes must be >= 0")
        if self.min_trade_count is not None and self.min_trade_count < 0:
            raise ValueError("case.backtest.min_trade_count must be >= 0")
        if (
            self.evaluation_start_at is None
            and self.evaluation_end_at is not None
            or self.evaluation_start_at is not None
            and self.evaluation_end_at is None
        ):
            raise ValueError(
                "case.backtest.evaluation_start_at and evaluation_end_at must be set together"
            )
        if (
            self.evaluation_start_at is not None
            and self.evaluation_end_at is not None
            and self.evaluation_start_at >= self.evaluation_end_at
        ):
            raise ValueError(
                "case.backtest.evaluation_start_at must be before evaluation_end_at"
            )
        return self


class BacktestSuiteResampling(BaseModel):
    method: Literal["none", "return_bootstrap", "block_bootstrap"] = "none"
    iterations: int = 100
    seed: int = 0
    block_size: int = 1

    @model_validator(mode="after")
    def validate_resampling(self) -> BacktestSuiteResampling:
        if self.iterations <= 0:
            raise ValueError("case.resampling.iterations must be positive")
        if self.block_size <= 0:
            raise ValueError("case.resampling.block_size must be positive")
        if self.method == "return_bootstrap" and self.block_size != 1:
            raise ValueError("case.resampling.block_size is only used for block_bootstrap")
        return self


class BacktestSuiteCase(BaseModel):
    case_id: str
    enabled: bool = True
    backtest: BacktestSuiteBacktestOverrides = Field(default_factory=BacktestSuiteBacktestOverrides)
    resampling: BacktestSuiteResampling = Field(default_factory=BacktestSuiteResampling)

    @model_validator(mode="after")
    def validate_case(self) -> BacktestSuiteCase:
        if not self.case_id.strip():
            raise ValueError("case_id must be non-empty")
        return self


class BacktestSuiteMember(BaseModel):
    spec_path: str
    enabled: bool = True
    case_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_member(self) -> BacktestSuiteMember:
        if not self.spec_path.strip():
            raise ValueError("suite member spec_path must be non-empty")
        return self


class StrategyBacktestSuiteSpec(BaseModel):
    schema_version: Literal["strategy_backtest_suite.v1"]
    suite_id: str
    selection_metric: str = "total_return"
    selection_direction: Literal["maximize", "minimize", "auto"] = "maximize"
    cases: list[BacktestSuiteCase]
    members: list[BacktestSuiteMember]

    @model_validator(mode="after")
    def validate_suite(self) -> StrategyBacktestSuiteSpec:
        if not self.suite_id.strip():
            raise ValueError("suite_id must be non-empty")
        enabled_cases = [case for case in self.cases if case.enabled]
        enabled_members = [member for member in self.members if member.enabled]
        if not enabled_cases:
            raise ValueError("suite must include at least one enabled case")
        if not enabled_members:
            raise ValueError("suite must include at least one enabled member")
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("suite case_id values must be unique")
        known_case_ids = set(case_ids)
        for member in self.members:
            unknown = sorted(set(member.case_ids) - known_case_ids)
            if unknown:
                raise ValueError(f"suite member references unknown case_ids: {unknown}")
        return self
