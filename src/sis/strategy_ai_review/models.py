from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


AI_REVIEW_PACKET_SCHEMA_VERSION = "strategy_ai_review_packet.v1"
AI_REVIEW_NOTE_SCHEMA_VERSION = "strategy_ai_review_note.v1"


class AIReviewPacketStatus(StrEnum):
    READY_FOR_AI_REVIEW = "READY_FOR_AI_REVIEW"
    NO_SOURCES = "NO_SOURCES"
    BLOCKED_SENSITIVE_SOURCE = "BLOCKED_SENSITIVE_SOURCE"


class AIReviewRecommendation(StrEnum):
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    REJECT = "REJECT"
    REVISE = "REVISE"
    EXTEND_OBSERVATION = "EXTEND_OBSERVATION"
    NO_ACTION = "NO_ACTION"


class AIReviewSourceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    schema_version: str | None = None
    strategy_id: str | None = None
    status: str | None = None
    action: str | None = None

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


class StrategyAIReviewPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_ai_review_packet.v1"] = AI_REVIEW_PACKET_SCHEMA_VERSION
    packet_id: str
    generated_at: datetime
    producer: StageProducer
    packet_status: AIReviewPacketStatus
    source_summaries: list[AIReviewSourceSummary]
    sensitive_source_count: int = Field(ge=0)
    review_questions: list[str] = Field(default_factory=list)
    ai_input_hash: str
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    permission_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("packet_id")
    @classmethod
    def validate_packet_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("packet_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("ai_input_hash")
    @classmethod
    def validate_ai_input_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("ai_input_hash must match sha256:<64 lowercase hex>")
        return value

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class AIReviewPacketReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    ai_input_hash: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("sha256", "ai_input_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("hash must match sha256:<64 lowercase hex>")
        return value


class StrategyAIReviewNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_ai_review_note.v1"] = AI_REVIEW_NOTE_SCHEMA_VERSION
    note_id: str
    recorded_at: datetime
    producer: StageProducer
    source_packet: AIReviewPacketReference
    provider: str
    model: str
    prompt_hash: str
    input_hash: str
    limitations: list[str]
    findings: list[str]
    recommendation: AIReviewRecommendation
    disagreements: list[str] = Field(default_factory=list)
    auto_applied: Literal[False] = False
    permission_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("note_id")
    @classmethod
    def validate_note_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("note_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("provider", "model", "prompt_hash", "input_hash")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped

    @field_validator("prompt_hash", "input_hash")
    @classmethod
    def validate_note_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("hash must match sha256:<64 lowercase hex>")
        return value

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
