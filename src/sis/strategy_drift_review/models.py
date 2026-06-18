from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_runtime_observation.models import (
    RuntimeObservationIngestStatus,
    RuntimeObservationSourceStage,
)
from sis.strategy_stage.models import StageCondition, StageProducer, StageSafetyBoundary


DRIFT_REVIEW_SCHEMA_VERSION = "paper_vs_backtest_drift_review.v1"


class DriftReviewStatus(StrEnum):
    READY_FOR_HUMAN_DRIFT_REVIEW = "READY_FOR_HUMAN_DRIFT_REVIEW"
    NEEDS_RUNTIME_OBSERVATION = "NEEDS_RUNTIME_OBSERVATION"
    NEEDS_BACKTEST_RESULT = "NEEDS_BACKTEST_RESULT"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class DriftReviewAction(StrEnum):
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    EXTEND_OBSERVATION = "EXTEND_OBSERVATION"
    REVISE_STRATEGY = "REVISE_STRATEGY"
    REPAIR_ARTIFACTS = "REPAIR_ARTIFACTS"


class DriftReviewSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: str
    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("artifact_key")
    @classmethod
    def validate_artifact_key(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact_key must not be empty")
        return stripped

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value


class DriftBacktestSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    backtest_passed: bool
    signals_considered: int = Field(ge=0)
    executed_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    trade_count: int = Field(ge=0)
    total_return: float
    max_drawdown: float | None = None
    win_rate: float | None = Field(default=None, ge=0, le=1)


class DriftRuntimeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    session_id: str
    source_stage: RuntimeObservationSourceStage
    ingest_status: RuntimeObservationIngestStatus
    ledger_entry_count: int = Field(ge=0)
    paper_fill_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    no_fill_count: int = Field(ge=0)
    max_observed_spread_bps: float | None = None
    max_observed_quote_age_ms: int | None = Field(default=None, ge=0)
    pnl_available: bool = False
    pnl_unavailable_reason: str | None = None
    realized_pnl_usd_total: float | None = None
    gross_pnl_usd_total: float | None = None
    fee_usd_total: float | None = None
    slippage_usd_total: float | None = None
    avg_slippage_bps: float | None = None
    max_abs_slippage_bps: float | None = None
    avg_fill_price_drift_bps: float | None = None
    max_abs_fill_price_drift_bps: float | None = None
    filled_notional_usd_total: float | None = None
    order_lifecycle_counts: dict[str, int] = Field(default_factory=dict)


class DriftMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtime_to_backtest_trade_count_ratio: float | None = None
    runtime_blocked_rate: float | None = Field(default=None, ge=0, le=1)
    runtime_no_fill_rate: float | None = Field(default=None, ge=0, le=1)
    max_observed_spread_bps: float | None = None
    max_observed_quote_age_ms: int | None = Field(default=None, ge=0)
    pnl_drift_available: bool = False
    backtest_total_return: float | None = None
    runtime_return_on_filled_notional: float | None = None
    runtime_vs_backtest_return_drift: float | None = None
    runtime_realized_pnl_usd_total: float | None = None
    runtime_fee_usd_total: float | None = None
    runtime_slippage_usd_total: float | None = None
    runtime_avg_slippage_bps: float | None = None
    runtime_max_abs_slippage_bps: float | None = None
    runtime_avg_fill_price_drift_bps: float | None = None
    runtime_max_abs_fill_price_drift_bps: float | None = None


class PaperVsBacktestDriftReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["paper_vs_backtest_drift_review.v1"] = DRIFT_REVIEW_SCHEMA_VERSION
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    review_status: DriftReviewStatus
    recommended_action: DriftReviewAction
    source_artifacts: list[DriftReviewSourceArtifact]
    backtest_summary: DriftBacktestSummary | None = None
    runtime_summary: DriftRuntimeSummary | None = None
    drift_metrics: DriftMetrics
    passed_conditions: list[StageCondition]
    failed_conditions: list[StageCondition]
    warning_conditions: list[StageCondition]
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("strategy_id")
    @classmethod
    def validate_strategy_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("strategy_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
