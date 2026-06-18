from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


DAILY_BRIEF_SCHEMA_VERSION = "strategy_daily_brief.v1"


class DailyBriefItemCategory(StrEnum):
    BROKEN_ARTIFACT = "broken_artifact"
    PENDING_HUMAN_REVIEW = "pending_human_review"
    NORMAL_PAPER_GAP = "normal_paper_gap"
    DRIFT_REVIEW_NEEDED = "drift_review_needed"
    LEARNING_REQUEST_PENDING = "learning_request_pending"
    BOUNDARY_VIOLATION = "boundary_violation"


class DailyBriefItemSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DailyBriefSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str | None = None
    schema_version: str | None = None

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


class DailyBriefItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: DailyBriefItemCategory
    severity: DailyBriefItemSeverity
    path: str
    schema_version: str | None = None
    strategy_id: str | None = None
    status: str | None = None
    action: str | None = None
    reason: str
    sha256: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("sha256")
    @classmethod
    def validate_item_sha256(cls, value: str | None) -> str | None:
        if value is not None and not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value


class DailyBriefSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scanned_json_count: int = Field(ge=0)
    broken_artifact_count: int = Field(ge=0)
    pending_human_review_count: int = Field(ge=0)
    normal_paper_gap_count: int = Field(ge=0)
    drift_review_needed_count: int = Field(ge=0)
    learning_request_pending_count: int = Field(ge=0)
    boundary_violation_count: int = Field(ge=0)
    total_item_count: int = Field(ge=0)


class StrategyDailyBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_daily_brief.v1"] = DAILY_BRIEF_SCHEMA_VERSION
    generated_at: datetime
    producer: StageProducer
    data_dir: str
    source_artifacts: list[DailyBriefSourceArtifact]
    summary: DailyBriefSummary
    items: list[DailyBriefItem]
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("data_dir")
    @classmethod
    def validate_data_dir(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
