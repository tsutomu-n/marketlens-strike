from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


CASE_LITE_SCHEMA_VERSION = "strategy_case_lite.v1"


class StrategyCaseArtifactType(StrEnum):
    STAGE_DECISION = "strategy_stage_decision"
    RUNTIME_OBSERVATION = "strategy_runtime_observation_manifest"
    DRIFT_REVIEW = "paper_vs_backtest_drift_review"
    LEARNING_EVENT = "strategy_learning_event"
    REVISION_REQUEST = "strategy_revision_request"
    AUTHORING_UPDATE_HANDOFF = "strategy_authoring_update_handoff"
    MICRO_LIVE_PLAN = "strategy_micro_live_plan"
    LIVE_OBSERVATION = "strategy_live_observation_manifest"
    SCALE_DECISION = "strategy_scale_decision"
    NEXT_SCALE_PLAN = "strategy_next_scale_plan"
    GENERIC = "generic"


class StrategyCaseSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: StrategyCaseArtifactType
    path: str
    sha256: str
    schema_version: str | None = None

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


class StrategyCaseTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: StrategyCaseArtifactType
    path: str
    sha256: str
    schema_version: str | None = None
    event_time: str | None = None
    status: str | None = None
    action: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)

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


class StrategyCaseLiteSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_count: int = Field(ge=0)
    timeline_count: int = Field(ge=0)
    latest_status: str | None = None
    open_actions: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    latest_source_hashes: dict[str, str] = Field(default_factory=dict)


class StrategyCaseLite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_case_lite.v1"] = CASE_LITE_SCHEMA_VERSION
    strategy_id: str
    case_id: str
    updated_at: datetime
    producer: StageProducer
    source_artifacts: list[StrategyCaseSourceArtifact]
    timeline: list[StrategyCaseTimelineEntry]
    summary: StrategyCaseLiteSummary
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("strategy_id", "case_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
