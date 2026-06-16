from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = "strategy_review_manifest.v1"
REVIEW_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


class ReviewStatus(StrEnum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    INCOMPLETE_ARTIFACTS = "INCOMPLETE_ARTIFACTS"
    INVALID_INPUT = "INVALID_INPUT"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class SourceArtifactStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"


class ReviewPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_dir: str
    review_markdown_path: str
    manifest_path: str


class ReviewSafety(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False


class EvaluationFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_validation_status: str | None = None
    pack_validation_pass_is_readiness_proof: Literal[False] = False


class ReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_required_count: int = Field(ge=0)
    invalid_required_count: int = Field(ge=0)
    boundary_violation_count: int = Field(ge=0)


class SourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: str
    path: str
    exists: bool
    required: bool
    status: SourceArtifactStatus
    sha256: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value

    @model_validator(mode="after")
    def validate_status_shape(self) -> SourceArtifact:
        if self.status is SourceArtifactStatus.PRESENT and not self.exists:
            raise ValueError("present source artifact must exist")
        if self.status is SourceArtifactStatus.PRESENT and self.sha256 is None:
            raise ValueError("present source artifact must include sha256")
        if self.status is SourceArtifactStatus.MISSING and self.sha256 is not None:
            raise ValueError("missing source artifact must omit sha256")
        return self


class StrategyReviewManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_review_manifest.v1"] = SCHEMA_VERSION
    review_id: str
    created_at: str
    review_status: ReviewStatus
    strict: bool
    paths: ReviewPaths
    source_artifacts: list[SourceArtifact]
    safety: ReviewSafety
    evaluation_flags: EvaluationFlags
    summary: ReviewSummary

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("review_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        if "/" in value or "\\" in value or value.startswith(".") or ".." in value:
            raise ValueError("review_id must be a single safe path segment")
        return value
