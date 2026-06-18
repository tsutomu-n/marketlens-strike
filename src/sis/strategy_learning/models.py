from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_runtime_observation.models import RuntimeObservationSourceStage
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


LEARNING_EVENT_SCHEMA_VERSION = "strategy_learning_event.v1"
REVISION_REQUEST_SCHEMA_VERSION = "strategy_revision_request.v1"
REVISION_REQUEST_REVIEW_SCHEMA_VERSION = "strategy_revision_request_review.v1"
AUTHORING_UPDATE_HANDOFF_SCHEMA_VERSION = "strategy_authoring_update_handoff.v1"


class LearningEventType(StrEnum):
    EXECUTION_ASSUMPTION_UPDATE = "execution_assumption_update"
    INSUFFICIENT_OBSERVATION = "insufficient_observation"
    ARTIFACT_BOUNDARY_VIOLATION = "artifact_boundary_violation"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class LearningRecommendedAction(StrEnum):
    REVISE_STRATEGY = "revise_strategy"
    EXTEND_OBSERVATION = "extend_observation"
    REPAIR_ARTIFACTS = "repair_artifacts"
    REVIEW_MANUALLY = "review_manually"


class RevisionRequestStatus(StrEnum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    NO_REVISION_REQUIRED = "NO_REVISION_REQUIRED"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class RevisionRequestReviewDecision(StrEnum):
    REJECT = "REJECT"
    NEEDS_FIX = "NEEDS_FIX"
    HOLD = "HOLD"
    REVIEWED_FOR_CONTEXT = "REVIEWED_FOR_CONTEXT"
    APPROVE_FOR_AUTHORING_UPDATE = "APPROVE_FOR_AUTHORING_UPDATE"


class AuthoringUpdateHandoffStatus(StrEnum):
    READY_FOR_HUMAN_AUTHORING_UPDATE = "READY_FOR_HUMAN_AUTHORING_UPDATE"
    NEEDS_REVISION_REVIEW_APPROVAL = "NEEDS_REVISION_REVIEW_APPROVAL"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class LearningSourceArtifact(BaseModel):
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


class StrategyLearningEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_learning_event.v1"] = LEARNING_EVENT_SCHEMA_VERSION
    learning_event_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    source_stage: RuntimeObservationSourceStage | Literal["drift_review"]
    source_artifacts: list[LearningSourceArtifact]
    event_type: LearningEventType
    finding: str
    impact: str
    recommended_action: LearningRecommendedAction
    source_review_status: str
    source_recommended_action: str
    requires_human_review: Literal[True] = True
    auto_applied: Literal[False] = False
    direct_spec_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("learning_event_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("finding", "impact", "source_review_status", "source_recommended_action")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class StrategyRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_revision_request.v1"] = REVISION_REQUEST_SCHEMA_VERSION
    revision_request_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    request_status: RevisionRequestStatus
    reason: str
    source_learning_event_ids: list[str]
    source_artifacts: list[LearningSourceArtifact]
    requested_changes: list[str]
    decision_needed: Literal["REVIEW_AND_AUTHORING_UPDATE"] = "REVIEW_AND_AUTHORING_UPDATE"
    requires_human_review: Literal[True] = True
    auto_applied: Literal[False] = False
    direct_spec_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("revision_request_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("source_learning_event_ids", "requested_changes")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("string lists must not contain empty items")
        return cleaned

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be empty")
        return stripped

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class RevisionRequestReviewSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_request_path: str
    revision_request_sha256: str
    revision_request_id: str
    request_status: RevisionRequestStatus
    requested_change_count: int = Field(ge=0)
    source_learning_event_count: int = Field(ge=0)
    auto_applied: Literal[False] = False
    direct_spec_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False

    @field_validator("revision_request_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("revision_request_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value

    @field_validator("revision_request_id")
    @classmethod
    def validate_revision_request_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("revision_request_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value


class StrategyRevisionRequestReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_revision_request_review.v1"] = (
        REVISION_REQUEST_REVIEW_SCHEMA_VERSION
    )
    revision_request_id: str
    strategy_id: str
    reviewed_at: datetime
    producer: StageProducer
    reviewer: str
    decision: RevisionRequestReviewDecision
    rationale: str
    required_actions: list[str]
    source_revision_request: RevisionRequestReviewSource
    authoring_update_input_allowed: bool
    requires_human_authoring_update: Literal[True] = True
    auto_applied: Literal[False] = False
    direct_spec_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("revision_request_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("reviewer", "rationale")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped

    @field_validator("required_actions")
    @classmethod
    def validate_required_actions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("required_actions must not contain empty items")
        return cleaned

    @field_serializer("reviewed_at")
    def serialize_reviewed_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @field_validator("authoring_update_input_allowed")
    @classmethod
    def validate_authoring_flag(cls, value: bool) -> bool:
        return value

    @field_validator("decision")
    @classmethod
    def validate_decision(
        cls, value: RevisionRequestReviewDecision
    ) -> RevisionRequestReviewDecision:
        return value

    @model_validator(mode="after")
    def validate_review_contract(self) -> StrategyRevisionRequestReview:
        if self.decision is RevisionRequestReviewDecision.NEEDS_FIX and not self.required_actions:
            raise ValueError("NEEDS_FIX requires at least one required action")
        if self.decision is RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE:
            if (
                self.source_revision_request.request_status
                is not RevisionRequestStatus.READY_FOR_HUMAN_REVIEW
            ):
                raise ValueError(
                    "APPROVE_FOR_AUTHORING_UPDATE requires READY_FOR_HUMAN_REVIEW request"
                )
            if self.source_revision_request.requested_change_count <= 0:
                raise ValueError("APPROVE_FOR_AUTHORING_UPDATE requires requested changes")
            if not self.authoring_update_input_allowed:
                raise ValueError(
                    "APPROVE_FOR_AUTHORING_UPDATE requires authoring_update_input_allowed"
                )
        elif self.authoring_update_input_allowed:
            raise ValueError("authoring_update_input_allowed requires APPROVE_FOR_AUTHORING_UPDATE")
        return self


class StrategyAuthoringUpdateHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_authoring_update_handoff.v1"] = (
        AUTHORING_UPDATE_HANDOFF_SCHEMA_VERSION
    )
    handoff_id: str
    revision_request_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    handoff_status: AuthoringUpdateHandoffStatus
    review_decision: RevisionRequestReviewDecision
    authoring_update_input_allowed: bool
    source_artifacts: list[LearningSourceArtifact]
    requested_changes: list[str]
    authoring_update_tasks: list[str]
    authoring_spec_path: str
    authoring_spec_sha256: str
    authoring_spec_schema_version: str | None = None
    authoring_spec_strategy_id: str | None = None
    strategy_id_matches_authoring_spec: bool | None = None
    requires_human_authoring_update: Literal[True] = True
    auto_applied: Literal[False] = False
    direct_spec_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("handoff_id", "revision_request_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("requested_changes", "authoring_update_tasks")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("string lists must not contain empty items")
        return cleaned

    @field_validator("authoring_spec_path")
    @classmethod
    def validate_authoring_spec_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("authoring_spec_sha256")
    @classmethod
    def validate_authoring_spec_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_handoff_contract(self) -> StrategyAuthoringUpdateHandoff:
        if (
            self.handoff_status is AuthoringUpdateHandoffStatus.READY_FOR_HUMAN_AUTHORING_UPDATE
            and self.review_decision
            is not RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE
        ):
            raise ValueError("ready handoff requires APPROVE_FOR_AUTHORING_UPDATE review")
        if (
            self.handoff_status is AuthoringUpdateHandoffStatus.READY_FOR_HUMAN_AUTHORING_UPDATE
            and not self.authoring_update_input_allowed
        ):
            raise ValueError("ready handoff requires authoring_update_input_allowed")
        if (
            self.review_decision is not RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE
            and self.authoring_update_input_allowed
        ):
            raise ValueError("authoring_update_input_allowed requires approved review")
        return self
