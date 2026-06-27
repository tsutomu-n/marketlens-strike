from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from sis.strategy_inputs.models import InputValidationStatus, ProducerInfo, SourceValidationStatus
from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path


CANDIDATE_SET_SCHEMA_VERSION = "strategy_idea_candidate_set.v1"
CANDIDATE_EXPORT_MANIFEST_SCHEMA_VERSION = "strategy_idea_candidate_export_manifest.v1"


class CandidateSetStatus(StrEnum):
    BUILT = "BUILT"
    BLOCKED_INPUT_EVIDENCE = "BLOCKED_INPUT_EVIDENCE"
    INVALID_CANDIDATE_SET = "INVALID_CANDIDATE_SET"


class CandidateDecision(StrEnum):
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"


class CandidateStatus(StrEnum):
    UNVERIFIED_CANDIDATE = "UNVERIFIED_CANDIDATE"


class SelectionAdjustedMetricsStatus(StrEnum):
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    AVAILABLE = "AVAILABLE"


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _validate_id(value: str, *, label: str) -> str:
    if not REVIEW_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must match ^[A-Za-z0-9][A-Za-z0-9._-]{{0,127}}$")
    return value


def _validate_non_empty(value: str, *, label: str = "value") -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} must not be empty")
    return stripped


def _validate_text_list(value: list[str], *, label: str) -> list[str]:
    cleaned = [item.strip() for item in value]
    if any(not item for item in cleaned):
        raise ValueError(f"{label} must not contain empty items")
    return cleaned


def _validate_unique(values: list[str], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicate ids")


class CandidateBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    permits_paper_candidate: Literal[False] = False
    permits_paper_intent_preview: Literal[False] = False
    auto_promote: Literal[False] = False
    generated_strategy_idea_is_final: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False


class TimeWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: datetime
    end: datetime

    @field_serializer("start", "end")
    def serialize_datetime(self, value: datetime) -> str:
        return _serialize_datetime(value)

    @model_validator(mode="after")
    def validate_order(self) -> TimeWindow:
        if self.start > self.end:
            raise ValueError("time window start must be before or equal to end")
        return self


class InputContractValidationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: str
    validation_path: str
    validation_sha256: str
    validation_status: InputValidationStatus

    @field_validator("contract_id")
    @classmethod
    def validate_contract_id(cls, value: str) -> str:
        return _validate_id(value, label="contract_id")

    @field_validator("validation_path")
    @classmethod
    def validate_validation_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("validation_sha256")
    @classmethod
    def validate_validation_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("validation_sha256 must match sha256:<64 lowercase hex>")
        return value


class CandidateSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    path: str
    sha256: str
    required: bool
    source_validation_status: SourceValidationStatus
    available_at: datetime
    max_observed_timestamp: datetime | None

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        return _validate_id(value, label="source_id")

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

    @field_serializer("available_at", "max_observed_timestamp")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return _serialize_datetime(value) if value is not None else None


class StrategyIdeaCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea_candidate_id: str
    candidate_status: Literal["UNVERIFIED_CANDIDATE"] = CandidateStatus.UNVERIFIED_CANDIDATE.value
    decision: CandidateDecision
    family: str
    title: str
    hypothesis_template: str
    mechanism_status: str
    signal_expression: str
    parameter_set: dict[str, Any] = Field(default_factory=dict)
    parameter_grid_ref: str
    target_definition: str
    prediction_horizon: str
    timeframe: str
    instruments: list[str] = Field(min_length=1)
    label_window: TimeWindow
    feature_observation_window: TimeWindow
    feature_columns_used: list[str] = Field(min_length=1)
    available_at_policy: str
    source_artifact_sha256: str
    trial_count_refs: list[str] = Field(default_factory=list)
    baseline_refs: list[str] = Field(default_factory=list)
    novelty_checks: dict[str, Any] = Field(default_factory=dict)
    raw_validation_metrics: dict[str, Any] = Field(default_factory=dict)
    selection_adjusted_metrics_status: SelectionAdjustedMetricsStatus
    leakage_checks: dict[str, Any]
    rejection_reason: str | None = None
    shortlist_reason: str | None = None
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_validator("idea_candidate_id")
    @classmethod
    def validate_idea_candidate_id(cls, value: str) -> str:
        return _validate_id(value, label="idea_candidate_id")

    @field_validator(
        "family",
        "title",
        "hypothesis_template",
        "mechanism_status",
        "signal_expression",
        "parameter_grid_ref",
        "target_definition",
        "prediction_horizon",
        "timeframe",
        "available_at_policy",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("instruments", "feature_columns_used", "trial_count_refs", "baseline_refs")
    @classmethod
    def validate_lists(cls, value: list[str]) -> list[str]:
        return _validate_text_list(value, label="list")

    @field_validator("source_artifact_sha256")
    @classmethod
    def validate_source_artifact_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("source_artifact_sha256 must match sha256:<64 lowercase hex>")
        return value

    @model_validator(mode="after")
    def validate_decision_shape(self) -> StrategyIdeaCandidate:
        if self.leakage_checks.get("uses_sealed_test_for_selection") is not False:
            raise ValueError("leakage_checks.uses_sealed_test_for_selection must be false")
        if self.decision is CandidateDecision.SHORTLISTED:
            if not self.shortlist_reason or not self.shortlist_reason.strip():
                raise ValueError("SHORTLISTED requires shortlist_reason")
            if self.rejection_reason is not None:
                raise ValueError("SHORTLISTED must not include rejection_reason")
        if self.decision is CandidateDecision.REJECTED:
            if not self.rejection_reason or not self.rejection_reason.strip():
                raise ValueError("REJECTED requires rejection_reason")
            if self.shortlist_reason is not None:
                raise ValueError("REJECTED must not include shortlist_reason")
        return self


class SearchLedgerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family_count: int = Field(ge=0)
    candidate_count_total: int = Field(ge=0)
    candidate_count_shortlisted: int = Field(ge=0)
    candidate_count_rejected: int = Field(ge=0)
    trial_count_total: int = Field(ge=0)
    parameter_grid_hash: str
    validation_peek_count: int = Field(ge=0)
    rerank_count: int = Field(ge=0)
    duplicate_rejection_count: int = Field(ge=0, default=0)
    success_only_reporting: Literal[False] = False
    sealed_test_used_for_selection: Literal[False] = False

    @field_validator("parameter_grid_hash")
    @classmethod
    def validate_parameter_grid_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("parameter_grid_hash must match sha256:<64 lowercase hex>")
        return value


class SelectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    description: str
    shortlisted_candidate_ids: list[str] = Field(default_factory=list)
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    known_gaps: list[str] = Field(default_factory=list)

    @field_validator("policy_id")
    @classmethod
    def validate_policy_id(cls, value: str) -> str:
        return _validate_id(value, label="policy_id")

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        return _validate_non_empty(value, label="description")

    @field_validator("shortlisted_candidate_ids", "rejected_candidate_ids", "known_gaps")
    @classmethod
    def validate_text_lists(cls, value: list[str]) -> list[str]:
        return _validate_text_list(value, label="list")


class SplitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    split_method: str
    train_window: TimeWindow
    validation_window: TimeWindow
    sealed_test_window: TimeWindow | None = None
    uses_sealed_test_for_selection: Literal[False] = False

    @field_validator("split_method")
    @classmethod
    def validate_split_method(cls, value: str) -> str:
        return _validate_non_empty(value, label="split_method")


class LeakagePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_available_at_policy: str
    purge_policy: str
    embargo_policy: str
    uses_sealed_test_for_selection: Literal[False] = False

    @field_validator("feature_available_at_policy", "purge_policy", "embargo_policy")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)


class StrategyIdeaCandidateSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_set.v1"] = CANDIDATE_SET_SCHEMA_VERSION
    candidate_set_id: str
    generated_at: datetime
    producer: ProducerInfo
    generator_version: str
    candidate_set_status: CandidateSetStatus
    input_contract_validation_refs: list[InputContractValidationRef] = Field(min_length=1)
    source_artifacts: list[CandidateSourceArtifact] = Field(min_length=1)
    candidate_inventory: list[StrategyIdeaCandidate] = Field(default_factory=list)
    search_ledger_summary: SearchLedgerSummary
    selection_policy: SelectionPolicy
    split_policy: SplitPolicy
    leakage_policy: LeakagePolicy
    dependency_versions: dict[str, str] = Field(min_length=1)
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_validator("candidate_set_id")
    @classmethod
    def validate_candidate_set_id(cls, value: str) -> str:
        return _validate_id(value, label="candidate_set_id")

    @field_validator("generator_version")
    @classmethod
    def validate_generator_version(cls, value: str) -> str:
        return _validate_non_empty(value, label="generator_version")

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return _serialize_datetime(value)

    @field_validator("dependency_versions")
    @classmethod
    def validate_dependency_versions(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, raw in value.items():
            cleaned_key = _validate_non_empty(key, label="dependency_versions key")
            cleaned_value = _validate_non_empty(raw, label="dependency_versions value")
            cleaned[cleaned_key] = cleaned_value
        return cleaned

    @model_validator(mode="after")
    def validate_candidate_set(self) -> StrategyIdeaCandidateSet:
        candidate_ids = [candidate.idea_candidate_id for candidate in self.candidate_inventory]
        _validate_unique(candidate_ids, label="candidate_inventory")
        inventory_ids = set(candidate_ids)
        shortlisted_ids = [
            candidate.idea_candidate_id
            for candidate in self.candidate_inventory
            if candidate.decision is CandidateDecision.SHORTLISTED
        ]
        rejected_ids = [
            candidate.idea_candidate_id
            for candidate in self.candidate_inventory
            if candidate.decision is CandidateDecision.REJECTED
        ]
        summary = self.search_ledger_summary
        if summary.candidate_count_total != len(self.candidate_inventory):
            raise ValueError("candidate_count_total must match candidate_inventory length")
        if summary.candidate_count_shortlisted != len(shortlisted_ids):
            raise ValueError("candidate_count_shortlisted must match candidate inventory")
        if summary.candidate_count_rejected != len(rejected_ids):
            raise ValueError("candidate_count_rejected must match candidate inventory")
        if summary.candidate_count_shortlisted + summary.candidate_count_rejected != (
            summary.candidate_count_total
        ):
            raise ValueError("shortlisted and rejected counts must add up to total")

        policy_shortlisted = self.selection_policy.shortlisted_candidate_ids
        policy_rejected = self.selection_policy.rejected_candidate_ids
        _validate_unique(policy_shortlisted, label="shortlisted_candidate_ids")
        _validate_unique(policy_rejected, label="rejected_candidate_ids")
        overlap = set(policy_shortlisted) & set(policy_rejected)
        if overlap:
            raise ValueError("shortlisted_candidate_ids and rejected_candidate_ids must not overlap")
        unknown_ids = (set(policy_shortlisted) | set(policy_rejected)) - inventory_ids
        if unknown_ids:
            unknown = ", ".join(sorted(unknown_ids))
            raise ValueError(f"unknown candidate id in selection_policy: {unknown}")
        if set(policy_shortlisted) != set(shortlisted_ids):
            raise ValueError("shortlisted_candidate_ids must match candidate inventory")
        if set(policy_rejected) != set(rejected_ids):
            raise ValueError("rejected_candidate_ids must match candidate inventory")

        non_pass_refs = [
            ref.contract_id
            for ref in self.input_contract_validation_refs
            if ref.validation_status is not InputValidationStatus.PASS
        ]
        if self.candidate_set_status is CandidateSetStatus.BUILT:
            if non_pass_refs:
                raise ValueError("BUILT requires PASS input contract validation refs")
            if not self.candidate_inventory:
                raise ValueError("BUILT requires at least one candidate")
            if shortlisted_ids and not rejected_ids:
                raise ValueError("success-only candidate inventory is not allowed")
            if any(source.max_observed_timestamp is None for source in self.source_artifacts):
                raise ValueError("BUILT requires max_observed_timestamp for source_artifacts")
        if self.candidate_set_status is CandidateSetStatus.BLOCKED_INPUT_EVIDENCE:
            if not non_pass_refs:
                raise ValueError("BLOCKED_INPUT_EVIDENCE requires non-PASS input validation")
            if self.candidate_inventory:
                raise ValueError("BLOCKED_INPUT_EVIDENCE must not include candidates")
            if summary.candidate_count_total != 0:
                raise ValueError("BLOCKED_INPUT_EVIDENCE requires zero candidate counts")
        return self


class CandidateExportedIdea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea_candidate_id: str
    strategy_idea_path: str
    strategy_idea_sha256: str
    export_decision: Literal["SHORTLISTED"] = CandidateDecision.SHORTLISTED.value

    @field_validator("idea_candidate_id")
    @classmethod
    def validate_idea_candidate_id(cls, value: str) -> str:
        return _validate_id(value, label="idea_candidate_id")

    @field_validator("strategy_idea_path")
    @classmethod
    def validate_strategy_idea_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("strategy_idea_sha256")
    @classmethod
    def validate_strategy_idea_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("strategy_idea_sha256 must match sha256:<64 lowercase hex>")
        return value


class CandidateExportManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_export_manifest.v1"] = (
        CANDIDATE_EXPORT_MANIFEST_SCHEMA_VERSION
    )
    manifest_id: str
    created_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    candidate_set_path: str
    candidate_set_sha256: str
    exported_ideas: list[CandidateExportedIdea] = Field(min_length=1)
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_validator("manifest_id", "candidate_set_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("candidate_set_path")
    @classmethod
    def validate_candidate_set_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("candidate_set_sha256")
    @classmethod
    def validate_candidate_set_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("candidate_set_sha256 must match sha256:<64 lowercase hex>")
        return value

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _serialize_datetime(value)
