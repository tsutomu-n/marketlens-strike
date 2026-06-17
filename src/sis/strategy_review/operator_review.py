from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from sis.backtest.artifact_io import sha256_file
from sis.strategy_review.manifest import (
    REVIEW_ID_PATTERN,
    SHA256_PATTERN,
    ReviewStatus,
    SourceArtifactStatus,
    SourceSafetyStatus,
    StrategyReviewManifest,
    _validate_manifest_path,
)
from sis.strategy_review.provenance import read_source_json, repo_relative_path


SCHEMA_VERSION = "operator_strategy_review.v1"


class OperatorReviewDecision(StrEnum):
    REJECT = "REJECT"
    NEEDS_FIX = "NEEDS_FIX"
    REVIEWED_FOR_CONTEXT = "REVIEWED_FOR_CONTEXT"
    PAPER_OBSERVATION_CANDIDATE = "PAPER_OBSERVATION_CANDIDATE"


class OperatorReviewProducer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal["sis"] = "sis"
    command: Literal["strategy-review-record"] = "strategy-review-record"
    schema_version: Literal["operator_strategy_review.v1"] = SCHEMA_VERSION


class OperatorReviewSourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_path: str
    review_manifest_sha256: str
    review_markdown_path: str
    review_markdown_sha256: str
    review_status: ReviewStatus
    source_safety_status: SourceSafetyStatus
    pack_validation_status: str | None = None
    lifecycle_review_status: SourceArtifactStatus
    missing_required_count: int = Field(ge=0)
    invalid_required_count: int = Field(ge=0)
    boundary_violation_count: int = Field(ge=0)
    unknown_boundary_count: int = Field(ge=0)

    @field_validator("manifest_path", "review_markdown_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        return _validate_manifest_path(value)

    @field_validator("review_manifest_sha256", "review_markdown_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must match sha256:<64 lowercase hex>")
        return value


class OperatorStrategyReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["operator_strategy_review.v1"] = SCHEMA_VERSION
    review_id: str
    reviewed_at: datetime
    producer: OperatorReviewProducer = Field(default_factory=OperatorReviewProducer)
    reviewer: str
    decision: OperatorReviewDecision
    rationale: str
    required_actions: list[str]
    live_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    source_review: OperatorReviewSourceReview

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("review_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("reviewer", "rationale")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
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

    @model_validator(mode="after")
    def validate_decision_contract(self) -> OperatorStrategyReview:
        if self.decision is OperatorReviewDecision.NEEDS_FIX and not self.required_actions:
            raise ValueError("NEEDS_FIX requires at least one required action")
        if self.decision is OperatorReviewDecision.PAPER_OBSERVATION_CANDIDATE:
            source = self.source_review
            if source.review_status is not ReviewStatus.READY_FOR_HUMAN_REVIEW:
                raise ValueError("PAPER_OBSERVATION_CANDIDATE requires READY_FOR_HUMAN_REVIEW")
            if source.source_safety_status is not SourceSafetyStatus.PASS:
                raise ValueError("PAPER_OBSERVATION_CANDIDATE requires PASS source safety")
            if source.pack_validation_status != "PASS":
                raise ValueError("PAPER_OBSERVATION_CANDIDATE requires PASS pack validation")
            if source.lifecycle_review_status is not SourceArtifactStatus.PRESENT:
                raise ValueError("PAPER_OBSERVATION_CANDIDATE requires present lifecycle review")
            if (
                source.missing_required_count
                or source.invalid_required_count
                or source.boundary_violation_count
                or source.unknown_boundary_count
            ):
                raise ValueError("PAPER_OBSERVATION_CANDIDATE requires zero blocking counts")
        return self


@dataclass(frozen=True)
class OperatorReviewRecordResult:
    operator_review: OperatorStrategyReview
    operator_review_path: Path


class OperatorReviewRecordError(ValueError):
    pass


class OperatorReviewOutputExistsError(OperatorReviewRecordError):
    pass


def _reviewed_at_value(reviewed_at: datetime | str | None) -> datetime:
    if isinstance(reviewed_at, str):
        return datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    value = reviewed_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise OperatorReviewRecordError(f"{label} missing: {repo_relative_path(path)}")
    if not path.is_file():
        raise OperatorReviewRecordError(f"{label} is not a file: {repo_relative_path(path)}")
    return path


def _load_strategy_review_manifest(manifest_path: Path) -> StrategyReviewManifest:
    try:
        payload = read_source_json(manifest_path)
    except Exception as exc:
        raise OperatorReviewRecordError(f"invalid review manifest: {exc}") from exc
    return StrategyReviewManifest.model_validate(payload)


def build_operator_source_review(review_dir: Path) -> OperatorReviewSourceReview:
    manifest_path = _required_file(review_dir / "review_manifest.json", "review manifest")
    markdown_path = _required_file(review_dir / "review.md", "review markdown")
    manifest = _load_strategy_review_manifest(manifest_path)

    expected_manifest_path = repo_relative_path(manifest_path)
    expected_markdown_path = repo_relative_path(markdown_path)
    if manifest.paths.manifest_path != expected_manifest_path:
        raise OperatorReviewRecordError(
            "review manifest path mismatch: "
            f"saved={manifest.paths.manifest_path} current={expected_manifest_path}"
        )
    if manifest.paths.review_markdown_path != expected_markdown_path:
        raise OperatorReviewRecordError(
            "review markdown path mismatch: "
            f"saved={manifest.paths.review_markdown_path} current={expected_markdown_path}"
        )

    lifecycle_artifact = next(
        (
            artifact
            for artifact in manifest.source_artifacts
            if artifact.artifact_key == "lifecycle_review"
        ),
        None,
    )
    lifecycle_status = (
        lifecycle_artifact.status
        if lifecycle_artifact is not None
        else SourceArtifactStatus.MISSING
    )

    return OperatorReviewSourceReview(
        manifest_path=expected_manifest_path,
        review_manifest_sha256=sha256_file(manifest_path),
        review_markdown_path=expected_markdown_path,
        review_markdown_sha256=sha256_file(markdown_path),
        review_status=manifest.review_status,
        source_safety_status=manifest.source_safety.status,
        pack_validation_status=manifest.evaluation_flags.pack_validation_status,
        lifecycle_review_status=lifecycle_status,
        missing_required_count=manifest.summary.missing_required_count,
        invalid_required_count=manifest.summary.invalid_required_count,
        boundary_violation_count=manifest.summary.boundary_violation_count,
        unknown_boundary_count=manifest.summary.unknown_boundary_count,
    )


def _operator_review_payload(operator_review: OperatorStrategyReview) -> dict[str, Any]:
    return operator_review.model_dump(mode="json", exclude_none=True)


def _write_operator_review(path: Path, operator_review: OperatorStrategyReview) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / ".operator_review.yaml.tmp"
    text = yaml.safe_dump(
        _operator_review_payload(operator_review),
        allow_unicode=True,
        sort_keys=False,
    )
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def record_operator_review(
    *,
    review_dir: Path,
    reviewer: str,
    decision: OperatorReviewDecision | str,
    rationale: str,
    required_actions: list[str] | None = None,
    replace_existing: bool = False,
    reviewed_at: datetime | str | None = None,
) -> OperatorReviewRecordResult:
    operator_review_path = review_dir / "operator_review.yaml"
    if operator_review_path.exists() and not replace_existing:
        raise OperatorReviewOutputExistsError(
            f"operator review already exists: {repo_relative_path(operator_review_path)}"
        )

    normalized_decision = (
        decision
        if isinstance(decision, OperatorReviewDecision)
        else OperatorReviewDecision(decision)
    )
    source_review = build_operator_source_review(review_dir)
    operator_review = OperatorStrategyReview(
        review_id=_load_strategy_review_manifest(review_dir / "review_manifest.json").review_id,
        reviewed_at=_reviewed_at_value(reviewed_at),
        reviewer=reviewer,
        decision=normalized_decision,
        rationale=rationale,
        required_actions=required_actions or [],
        source_review=source_review,
    )
    _write_operator_review(operator_review_path, operator_review)
    return OperatorReviewRecordResult(
        operator_review=operator_review,
        operator_review_path=operator_review_path,
    )


def _load_operator_review(path: Path) -> OperatorStrategyReview:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise OperatorReviewRecordError(f"invalid operator review YAML: {exc}") from exc
    except OSError as exc:
        raise OperatorReviewRecordError(f"operator review read failed: {exc}") from exc
    if not isinstance(loaded, dict):
        raise OperatorReviewRecordError("operator review YAML must contain an object")
    return OperatorStrategyReview.model_validate(loaded)


def validate_existing_operator_review(*, review_dir: Path) -> OperatorReviewRecordResult:
    operator_review_path = _required_file(review_dir / "operator_review.yaml", "operator review")
    operator_review = _load_operator_review(operator_review_path)
    current_source = build_operator_source_review(review_dir)
    expected_manifest_path = repo_relative_path(review_dir / "review_manifest.json")
    expected_markdown_path = repo_relative_path(review_dir / "review.md")

    if operator_review.source_review.manifest_path != expected_manifest_path:
        raise OperatorReviewRecordError(
            "operator review manifest path mismatch: "
            f"saved={operator_review.source_review.manifest_path} current={expected_manifest_path}"
        )
    if operator_review.source_review.review_markdown_path != expected_markdown_path:
        raise OperatorReviewRecordError(
            "operator review markdown path mismatch: "
            f"saved={operator_review.source_review.review_markdown_path} "
            f"current={expected_markdown_path}"
        )
    if (
        operator_review.source_review.review_manifest_sha256
        != current_source.review_manifest_sha256
    ):
        raise OperatorReviewRecordError("review manifest hash mismatch")
    if (
        operator_review.source_review.review_markdown_sha256
        != current_source.review_markdown_sha256
    ):
        raise OperatorReviewRecordError("review markdown hash mismatch")

    return OperatorReviewRecordResult(
        operator_review=operator_review,
        operator_review_path=operator_review_path,
    )
