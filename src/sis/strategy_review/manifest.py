from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = "strategy_review_manifest.v1"
REVIEW_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")
URL_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_PATH_SEGMENTS = {
    ".env",
    ".env.local",
    ".envrc",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credential",
    "secrets",
    "secret",
}


class ReviewStatus(StrEnum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    INCOMPLETE_ARTIFACTS = "INCOMPLETE_ARTIFACTS"
    INVALID_INPUT = "INVALID_INPUT"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class SourceArtifactStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"
    BLOCKED = "blocked"


class SourceSafetyStatus(StrEnum):
    PASS = "PASS"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


def _validate_manifest_path(value: str) -> str:
    if "\\" in value:
        raise ValueError("manifest paths must use POSIX separators")
    if value.startswith("/"):
        raise ValueError("manifest paths must be repository-relative")
    if URL_SCHEME_PATTERN.match(value):
        raise ValueError("manifest paths must not include URL schemes")
    if any(part == ".." for part in value.split("/")):
        raise ValueError("manifest paths must not contain ..")
    for part in value.split("/"):
        if part.startswith("."):
            raise ValueError("manifest paths must not include hidden path segments")
        if part.lower() in SECRET_PATH_SEGMENTS:
            raise ValueError("manifest paths must not include secret path segments")
    if value in {"", "."}:
        raise ValueError("manifest paths must not be empty")
    return value


class ReviewPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_dir: str
    review_markdown_path: str
    manifest_path: str

    @field_validator("review_dir", "review_markdown_path", "manifest_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        return _validate_manifest_path(value)


class BuilderSafety(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False


class SourceSafetyFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: bool = False
    live_conversion_allowed: bool = False
    wallet_used: bool = False
    signing_used: bool = False
    exchange_write_used: bool = False
    venue_write_used: bool = False


class SourceSafety(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SourceSafetyStatus
    boundary_violation_count: int = Field(ge=0)
    unknown_boundary_count: int = Field(ge=0)
    observed_flags: SourceSafetyFlags

    @model_validator(mode="after")
    def validate_counts(self) -> SourceSafety:
        if self.status is SourceSafetyStatus.BLOCKED and self.boundary_violation_count < 1:
            raise ValueError("BLOCKED source_safety requires boundary_violation_count >= 1")
        if self.status is SourceSafetyStatus.UNKNOWN and self.unknown_boundary_count < 1:
            raise ValueError("UNKNOWN source_safety requires unknown_boundary_count >= 1")
        if self.status is SourceSafetyStatus.PASS:
            if self.boundary_violation_count or self.unknown_boundary_count:
                raise ValueError("PASS source_safety requires zero violation and unknown counts")
        return self


class EvaluationFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_validation_status: str | None = None
    pack_validation_pass_is_readiness_proof: Literal[False] = False


class ReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_required_count: int = Field(ge=0)
    invalid_required_count: int = Field(ge=0)
    boundary_violation_count: int = Field(ge=0)
    unknown_boundary_count: int = Field(ge=0)


class ProducerInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal["sis"] = "sis"
    command: Literal["strategy-review-build"] = "strategy-review-build"
    schema_version: Literal["strategy_review_manifest.v1"] = SCHEMA_VERSION


class SourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: str
    path: str
    exists: bool
    required: bool
    status: SourceArtifactStatus
    sha256: str | None = None
    bytes: int | None = Field(default=None, ge=0)
    detected_schema_version: str | None = None
    error: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _validate_manifest_path(value)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value

    @model_validator(mode="after")
    def validate_status_shape(self) -> SourceArtifact:
        if self.status is SourceArtifactStatus.PRESENT:
            if not self.exists:
                raise ValueError("present source artifact must exist")
            if self.sha256 is None:
                raise ValueError("present source artifact must include sha256")
            if self.bytes is None:
                raise ValueError("present source artifact must include bytes")
        if self.status is SourceArtifactStatus.MISSING:
            if self.exists:
                raise ValueError("missing source artifact must not exist")
            if self.sha256 is not None:
                raise ValueError("missing source artifact must omit sha256")
            if self.bytes is not None:
                raise ValueError("missing source artifact must omit bytes")
        if self.status in {SourceArtifactStatus.INVALID, SourceArtifactStatus.BLOCKED}:
            if not self.exists:
                raise ValueError("invalid or blocked source artifact must exist")
            if not self.error:
                raise ValueError("invalid or blocked source artifact must include error")
        return self


class StrategyReviewManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_review_manifest.v1"] = SCHEMA_VERSION
    review_id: str
    created_at: str
    producer: ProducerInfo = Field(default_factory=ProducerInfo)
    review_status: ReviewStatus
    strict: bool
    paths: ReviewPaths
    source_artifacts: list[SourceArtifact]
    builder_safety: BuilderSafety
    source_safety: SourceSafety
    evaluation_flags: EvaluationFlags
    summary: ReviewSummary

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("review_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @model_validator(mode="after")
    def validate_status_safety_relationship(self) -> StrategyReviewManifest:
        if self.summary.boundary_violation_count != self.source_safety.boundary_violation_count:
            raise ValueError("summary.boundary_violation_count must match source_safety")
        if self.summary.unknown_boundary_count != self.source_safety.unknown_boundary_count:
            raise ValueError("summary.unknown_boundary_count must match source_safety")
        if (
            self.source_safety.status is SourceSafetyStatus.BLOCKED
            and self.review_status is not ReviewStatus.BLOCKED_BOUNDARY_VIOLATION
        ):
            raise ValueError("BLOCKED source_safety requires BLOCKED_BOUNDARY_VIOLATION")
        has_invalid_artifact = any(
            artifact.status is SourceArtifactStatus.INVALID for artifact in self.source_artifacts
        )
        if (
            self.source_safety.status is SourceSafetyStatus.UNKNOWN
            and not has_invalid_artifact
            and self.review_status is not ReviewStatus.INCOMPLETE_ARTIFACTS
        ):
            raise ValueError("UNKNOWN source_safety requires INCOMPLETE_ARTIFACTS")
        if (
            self.review_status is ReviewStatus.READY_FOR_HUMAN_REVIEW
            and self.source_safety.status is not SourceSafetyStatus.PASS
        ):
            raise ValueError("READY_FOR_HUMAN_REVIEW requires PASS source_safety")
        return self
