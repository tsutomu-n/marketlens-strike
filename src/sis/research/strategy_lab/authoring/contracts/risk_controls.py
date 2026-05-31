from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, model_validator


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
