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
AI_REVIEW_STRUCTURED_FINDINGS_SCHEMA_VERSION = "strategy_ai_review_structured_findings.v1"
AIReviewContextEntryValue = str | int | list[str] | None


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


class AIReviewModelReasoningEffort(StrEnum):
    MEDIUM = "medium"
    XHIGH = "xhigh"


class AIReviewStructuredFindingStatus(StrEnum):
    RECORDED = "RECORDED"


class AIReviewFindingType(StrEnum):
    SOURCE_ARTIFACT_REVIEW = "SOURCE_ARTIFACT_REVIEW"
    OPEN_ACTION_REVIEW = "OPEN_ACTION_REVIEW"
    CONTEXT_INSUFFICIENT = "CONTEXT_INSUFFICIENT"
    SAFETY_BOUNDARY = "SAFETY_BOUNDARY"
    OVERCLAIM_RISK = "OVERCLAIM_RISK"
    OTHER = "OTHER"


class AIReviewFindingSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AIReviewFindingImpact(StrEnum):
    INFORMATION_ONLY = "INFORMATION_ONLY"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    BLOCKING_CONTEXT_GAP = "BLOCKING_CONTEXT_GAP"


class AIReviewFindingNextAction(StrEnum):
    INSPECT_SOURCE_ARTIFACT = "INSPECT_SOURCE_ARTIFACT"
    INSPECT_DRIFT_EVIDENCE = "INSPECT_DRIFT_EVIDENCE"
    ADD_ALLOWLISTED_CONTEXT = "ADD_ALLOWLISTED_CONTEXT"
    RECORD_HUMAN_REVIEW = "RECORD_HUMAN_REVIEW"
    NO_ACTION = "NO_ACTION"


class AIReviewEvidenceRefType(StrEnum):
    NOTE_FINDING = "note_finding"
    NOTE_LIMITATION = "note_limitation"
    PACKET_SOURCE_SUMMARY = "packet_source_summary"
    PACKET_CONTEXT_SECTION = "packet_context_section"
    PACKET_CONTEXT_ENTRY = "packet_context_entry"


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


class AIReviewContextSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_type: str
    title: str
    source_path: str
    schema_version: str
    entries: dict[str, AIReviewContextEntryValue]

    @field_validator("section_type", "title", "schema_version")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("context section text fields must not be empty")
        return stripped

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)


class StrategyAIReviewPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_ai_review_packet.v1"] = AI_REVIEW_PACKET_SCHEMA_VERSION
    packet_id: str
    generated_at: datetime
    producer: StageProducer
    packet_status: AIReviewPacketStatus
    source_summaries: list[AIReviewSourceSummary]
    context_sections: list[AIReviewContextSection] = Field(default_factory=list)
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
    model_reasoning_effort: AIReviewModelReasoningEffort | None = None
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


class AIReviewSourceNoteReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    input_hash: str
    prompt_hash: str
    provider: str
    model: str
    recommendation: AIReviewRecommendation

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("sha256", "input_hash", "prompt_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("hash must match sha256:<64 lowercase hex>")
        return value

    @field_validator("provider", "model")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped


class AIReviewEvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_type: AIReviewEvidenceRefType
    index: int = Field(ge=0)
    entry_key: str | None = None

    @field_validator("entry_key")
    @classmethod
    def validate_entry_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("entry_key must not be empty")
        return stripped


class AIReviewStructuredFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    finding_type: AIReviewFindingType
    severity: AIReviewFindingSeverity
    review_impact: AIReviewFindingImpact
    statement: str
    evidence_refs: list[AIReviewEvidenceRef]
    recommended_next_action: AIReviewFindingNextAction
    limitations: list[str] = Field(default_factory=list)

    @field_validator("finding_id")
    @classmethod
    def validate_finding_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("finding_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("statement")
    @classmethod
    def validate_statement(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("statement must not be empty")
        return stripped


class StrategyAIReviewStructuredFindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_ai_review_structured_findings.v1"] = (
        AI_REVIEW_STRUCTURED_FINDINGS_SCHEMA_VERSION
    )
    finding_set_id: str
    recorded_at: datetime
    producer: StageProducer
    finding_set_status: AIReviewStructuredFindingStatus = AIReviewStructuredFindingStatus.RECORDED
    source_note: AIReviewSourceNoteReference
    source_packet: AIReviewPacketReference
    findings: list[AIReviewStructuredFinding]
    auto_applied: Literal[False] = False
    permission_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("finding_set_id")
    @classmethod
    def validate_finding_set_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("finding_set_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
