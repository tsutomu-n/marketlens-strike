from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.run_profile import DEFAULT_FORBIDDEN_CLAIMS, LEGACY_FORBIDDEN_CLAIMS

PROXY_REQUIREMENTS = {
    "XYZ100": {"QQQ"},
    "SP500": {"SPY"},
}


class SymbolBinding(BaseModel):
    execution_venue: Literal["trade_xyz"]
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
        expected = PROXY_REQUIREMENTS.get(execution_symbol)
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
    execution_venue: Literal["trade_xyz"]
    execution_symbol: str
    real_market_symbol: str
    side: Literal["long", "short", "none"]
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
    reason_codes: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_signal_record(self) -> StrategySignalRecord:
        if not self.execution_symbol.strip():
            raise ValueError("execution_symbol must be non-empty")
        if not self.real_market_symbol.strip():
            raise ValueError("real_market_symbol must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.rank_score is not None and not 0.0 <= self.rank_score <= 1.0:
            raise ValueError("rank_score must be between 0 and 1")
        if self.percentile_rank is not None and not 0.0 <= self.percentile_rank <= 1.0:
            raise ValueError("percentile_rank must be between 0 and 1")
        self.execution_symbol = self.execution_symbol.strip().upper()
        self.real_market_symbol = self.real_market_symbol.strip().upper()
        return self
