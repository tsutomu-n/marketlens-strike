from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageCondition, StageProducer, StageSafetyBoundary


PAPER_SMOKE_PLAN_SCHEMA_VERSION = "strategy_paper_smoke_plan.v1"


class PaperSmokePlanStatus(StrEnum):
    READY_TO_RUN_SMOKE_CYCLE = "READY_TO_RUN_SMOKE_CYCLE"
    NEEDS_SOURCE_ARTIFACTS = "NEEDS_SOURCE_ARTIFACTS"
    NEEDS_STAGE_APPROVAL = "NEEDS_STAGE_APPROVAL"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class PaperSmokeSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: str
    path: str
    exists: bool
    required: bool
    sha256: str | None = None
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
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value


class PaperSmokeThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_fills_for_pass: int = Field(ge=1)
    min_trading_days_for_pass: int = Field(ge=1)
    max_blocked_rate: float = Field(ge=0, le=1)
    max_consecutive_blocked: int = Field(ge=1)
    max_open_position_age_hours: float = Field(ge=0)
    max_order_notional_usd: float | None = Field(default=None, gt=0)
    max_position_notional_usd: float | None = Field(default=None, gt=0)
    max_orders_per_day: int | None = Field(default=None, ge=0)
    stop_after_consecutive_errors: int | None = Field(default=None, ge=0)


class PaperSmokeExecutionPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str
    smoke: Literal[True] = True
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("command must not be empty")
        return stripped


class StrategyPaperSmokePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_paper_smoke_plan.v1"] = PAPER_SMOKE_PLAN_SCHEMA_VERSION
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    plan_status: PaperSmokePlanStatus
    source_artifacts: list[PaperSmokeSourceArtifact]
    thresholds: PaperSmokeThresholds
    execution_preview: PaperSmokeExecutionPreview
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
