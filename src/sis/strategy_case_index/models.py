from __future__ import annotations

from datetime import datetime, timezone
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
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


CASE_INDEX_SCHEMA_VERSION = "strategy_case_index.v1"


class StrategyCaseIndexBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    db_persistence_allowed: Literal[False] = False


class StrategyCaseIndexSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    schema_version: Literal["strategy_case_lite.v1"] = "strategy_case_lite.v1"

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


class StrategyCaseIndexCaseEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    strategy_id: str
    case_path: str
    case_sha256: str
    latest_status: str | None = None
    artifact_count: int = Field(ge=0)
    timeline_count: int = Field(ge=0)
    open_actions: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    updated_at: datetime

    @field_validator("case_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("case_path")
    @classmethod
    def validate_case_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("case_sha256")
    @classmethod
    def validate_case_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("case_sha256 must match sha256:<64 lowercase hex>")
        return value

    @field_validator("open_actions", "blocked_reasons")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("string lists must not contain empty items")
        return cleaned

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class StrategyCaseIndexStrategySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    case_count: int = Field(ge=0)
    latest_case_id: str
    latest_case_path: str
    latest_status: str | None = None
    open_actions: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)

    @field_validator("strategy_id", "latest_case_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("latest_case_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("open_actions", "blocked_reasons")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("string lists must not contain empty items")
        return cleaned


class StrategyCaseIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_case_index.v1"] = CASE_INDEX_SCHEMA_VERSION
    index_id: str
    created_at: datetime
    producer: StageProducer
    case_count: int = Field(ge=0)
    strategy_count: int = Field(ge=0)
    cases: list[StrategyCaseIndexCaseEntry]
    strategies: list[StrategyCaseIndexStrategySummary]
    source_artifacts: list[StrategyCaseIndexSourceArtifact]
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)
    index_boundary: StrategyCaseIndexBoundary = Field(default_factory=StrategyCaseIndexBoundary)

    @field_validator("index_id")
    @classmethod
    def validate_index_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("index_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_counts(self) -> StrategyCaseIndex:
        if self.case_count != len(self.cases):
            raise ValueError("case_count must equal cases length")
        if self.strategy_count != len(self.strategies):
            raise ValueError("strategy_count must equal strategies length")
        if len(self.source_artifacts) != len(self.cases):
            raise ValueError("source_artifacts length must equal cases length")
        strategy_ids = {case.strategy_id for case in self.cases}
        summary_ids = {strategy.strategy_id for strategy in self.strategies}
        if strategy_ids != summary_ids:
            raise ValueError("strategies must summarize all case strategy_ids")
        return self
