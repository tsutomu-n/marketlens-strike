from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

EndPositionPolicy = Literal[
    "force_close_if_executable",
    "mark_to_market_only",
    "error_if_open",
]


class PeriodConfig(BaseModel):
    warmup_start_ts: datetime | None = None
    evaluation_start_ts: datetime
    evaluation_end_ts: datetime


class PositionSizingConfig(BaseModel):
    mode: Literal["fixed_notional"] = "fixed_notional"
    notional_usd: float = Field(gt=0)
    max_position_notional_usd: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_position_sizing(self) -> PositionSizingConfig:
        if (
            self.max_position_notional_usd is not None
            and self.notional_usd > self.max_position_notional_usd
        ):
            raise ValueError("notional_usd must be <= max_position_notional_usd")
        return self


class ExecutionConfig(BaseModel):
    side_mode: Literal["long_only"] = "long_only"
    fill_model: Literal["market_like_taker_v0"] = "market_like_taker_v0"
    extra_slippage_bps: float = Field(default=0.0, ge=0)
    force_close_on_end: bool = False
    end_position_policy: EndPositionPolicy | None = None

    @model_validator(mode="after")
    def validate_end_position_policy(self) -> ExecutionConfig:
        if self.end_position_policy is None:
            self.end_position_policy = (
                "force_close_if_executable" if self.force_close_on_end else "mark_to_market_only"
            )
        return self


class CostConfig(BaseModel):
    fee_model_ref: str = "configs/fee_model.trade_xyz.yaml"
    fee_scenario: Literal["row_resolved", "standard", "growth"] = "row_resolved"
    fee_multiplier: float = Field(default=1.0, gt=0)
    funding_policy: Literal[
        "disabled_v0",
        "nullable_zero_v0",
        "fixture_hourly_v0",
    ] = "nullable_zero_v0"


class GateConfig(BaseModel):
    allow_entry_when_block_reasons_non_empty: bool = False
    allow_entry_when_is_tradable_false: bool = False
    max_spread_bps: float | None = Field(default=None, gt=0)
    min_depth_10bps_usd: float | None = Field(default=None, gt=0)
    max_bound_distance: float | None = Field(default=None, ge=0)
    max_oi_cap_usage: float | None = Field(default=None, ge=0)


class LeverageConfig(BaseModel):
    mode: Literal["disabled"] = "disabled"
    requested_leverage: None = None
    max_leverage: None = None
    liquidation_model: Literal["not_implemented"] = "not_implemented"


class ReportConfig(BaseModel):
    write_markdown: bool = True
    write_html: bool = True
    write_svg_charts: bool = True
    write_charts_data_json: bool = True


class BacktestConfig(BaseModel):
    schema_version: Literal["trade_xyz_backtest_config.v1"] = "trade_xyz_backtest_config.v1"
    run_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    period: PeriodConfig
    initial_cash_usd: float = Field(gt=0)
    position_sizing: PositionSizingConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    cost: CostConfig = Field(default_factory=CostConfig)
    gates: GateConfig = Field(default_factory=GateConfig)
    leverage: LeverageConfig = Field(default_factory=LeverageConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    deterministic_seed: int = 0

    @model_validator(mode="after")
    def validate_config(self) -> BacktestConfig:
        if self.period.evaluation_start_ts >= self.period.evaluation_end_ts:
            raise ValueError("evaluation_start_ts must be < evaluation_end_ts")
        if (
            self.period.warmup_start_ts is not None
            and self.period.warmup_start_ts > self.period.evaluation_start_ts
        ):
            raise ValueError("warmup_start_ts must be <= evaluation_start_ts")
        self.symbol = self.symbol.strip().upper()
        if not self.run_id.strip():
            raise ValueError("run_id must be non-empty")
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must be non-empty")
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if not self.timeframe.strip():
            raise ValueError("timeframe must be non-empty")
        return self
