from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageCondition, StageProducer, StageSafetyBoundary


SCALE_DECISION_SCHEMA_VERSION = "strategy_scale_decision.v1"


class ScaleDecisionStatus(StrEnum):
    READY_FOR_HUMAN_SCALE_REVIEW = "READY_FOR_HUMAN_SCALE_REVIEW"
    NEEDS_LIVE_OBSERVATION = "NEEDS_LIVE_OBSERVATION"
    NEEDS_REPAIR = "NEEDS_REPAIR"
    REVISE_OR_RETIRE = "REVISE_OR_RETIRE"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class ScaleRecommendedAction(StrEnum):
    PREPARE_NEXT_SCALE_PLAN = "PREPARE_NEXT_SCALE_PLAN"
    HOLD_AT_MICRO_LIVE = "HOLD_AT_MICRO_LIVE"
    REVISE_STRATEGY = "REVISE_STRATEGY"
    RETIRE_STRATEGY = "RETIRE_STRATEGY"
    REPAIR_ARTIFACTS = "REPAIR_ARTIFACTS"


class ScaleDecisionSourceArtifact(BaseModel):
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


class ScaleDecisionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_actual_fill: bool = False
    require_cancel_or_close_observed: bool = True
    allow_rejection: bool = False
    allow_blocked_canary: bool = False
    allow_max_loss_breach: bool = False


class StrategyScaleDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_scale_decision.v1"] = SCALE_DECISION_SCHEMA_VERSION
    decision_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    decision_status: ScaleDecisionStatus
    recommended_action: ScaleRecommendedAction
    policy: ScaleDecisionPolicy
    source_artifacts: list[ScaleDecisionSourceArtifact]
    passed_conditions: list[StageCondition]
    failed_conditions: list[StageCondition]
    warning_conditions: list[StageCondition]
    required_human_review: Literal[True] = True
    next_scale_plan_allowed: Literal[False] = False
    scale_up_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("decision_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
