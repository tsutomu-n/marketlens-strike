from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
