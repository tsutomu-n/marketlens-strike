from __future__ import annotations

from datetime import datetime
from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ReviewSeverity = Literal["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]
ReviewDecision = Literal[
    "APPROVE",
    "APPROVE_WITH_WARNINGS",
    "REVISE_REQUIRED",
    "REJECT_SEED",
    "INSUFFICIENT_EVIDENCE",
]
ReviewMode = Literal["standard", "adversarial"]
CoverageStatus = Literal["ok", "concern", "gap", "not_reviewed"]
ExitGateDecision = Literal["APPROVE_2_3", "REVISE_2_2", "REJECT_SEED"]

PACK_HASH_PATTERN = r"^sha256:[a-fA-F0-9]{64}$"
PROMPT_CONTRACT_VERSION = "llm_dag_review_prompt.v1"


def _validate_catalog_refs(values: list[str]) -> list[str]:
    invalid = [value for value in values if not value.startswith("CAT.")]
    if invalid:
        raise ValueError("evidence_refs must use CAT.* ids: " + ", ".join(invalid))
    return values


class ReviewerMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    invocation: str = Field(min_length=1)
    temperature: float


class LlmReviewCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    causal_structure: CoverageStatus
    temporal_leakage: CoverageStatus
    market_structure: CoverageStatus
    counter_dag_coverage: CoverageStatus
    repo_boundary: CoverageStatus


class LlmReviewSeverityCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    BLOCKER: int = Field(ge=0)
    HIGH: int = Field(ge=0)
    MEDIUM: int = Field(ge=0)
    LOW: int = Field(ge=0)
    INFO: int = Field(ge=0)

    def as_dict(self) -> dict[ReviewSeverity, int]:
        return {
            "BLOCKER": self.BLOCKER,
            "HIGH": self.HIGH,
            "MEDIUM": self.MEDIUM,
            "LOW": self.LOW,
            "INFO": self.INFO,
        }


class LlmReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1)
    severity: ReviewSeverity
    category: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    target_refs: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    requires_human_decision: bool
    human_decision_id: str | None = None

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        return _validate_catalog_refs(values)

    @model_validator(mode="after")
    def validate_human_decision_link(self) -> Self:
        if self.requires_human_decision and self.human_decision_id is None:
            raise ValueError("human_decision_id is required when requires_human_decision=true")
        if not self.requires_human_decision and self.human_decision_id is not None:
            raise ValueError("human_decision_id must be null unless requires_human_decision=true")
        return self


class LlmRequiredHumanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=1)
    recommended_option: str | None = None
    evidence_refs: list[str] = Field(min_length=1)

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        return _validate_catalog_refs(values)


class LlmDagReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["llm_dag_review.v1"]
    review_id: str = Field(min_length=1)
    dag_id: str = Field(min_length=1)
    pack_hash: str = Field(pattern=PACK_HASH_PATTERN)
    prompt_contract_version: Literal["llm_dag_review_prompt.v1"]
    prompt_hash: str | None = None
    review_mode: ReviewMode
    reviewer: ReviewerMetadata
    overall_decision: ReviewDecision
    coverage: LlmReviewCoverage
    severity_counts: LlmReviewSeverityCounts
    findings: list[LlmReviewFinding] = Field(default_factory=list)
    required_human_decisions: list[LlmRequiredHumanDecision] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_cross_references(self) -> Self:
        counts = {key: 0 for key in self.severity_counts.as_dict()}
        for finding in self.findings:
            counts[finding.severity] += 1
        if counts != self.severity_counts.as_dict():
            raise ValueError(f"severity_counts mismatch: expected {counts}")

        decisions = {decision.decision_id for decision in self.required_human_decisions}
        unknown = sorted(
            {
                finding.human_decision_id
                for finding in self.findings
                if finding.human_decision_id is not None
                and finding.human_decision_id not in decisions
            }
        )
        if unknown:
            raise ValueError("unknown human_decision_id: " + ", ".join(unknown))
        return self


class HumanResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    selected_option: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    resolved_by: str = Field(min_length=1)
    resolved_at: datetime


class Layer22HumanResolutions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["layer_2_2_human_resolutions.v1"]
    dag_id: str = Field(min_length=1)
    pack_hash: str = Field(pattern=PACK_HASH_PATTERN)
    resolutions: list[HumanResolution] = Field(default_factory=list)

    def resolved_decision_ids(self) -> set[str]:
        return {item.decision_id for item in self.resolutions}


class Layer22ExitDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["layer_2_2_exit_decision.v1"]
    dag_id: str = Field(min_length=1)
    decision: ExitGateDecision
    pack_hash: str = Field(pattern=PACK_HASH_PATTERN)
    review_ids: list[str] = Field(min_length=1)
    unresolved_human_decisions: list[str] = Field(default_factory=list)
    blocker_count: int = Field(ge=0)
    high_count: int = Field(ge=0)
    second_review_required: bool
    created_at: datetime

    @model_validator(mode="after")
    def validate_approve_invariants(self) -> Self:
        if self.decision != "APPROVE_2_3":
            return self
        if self.second_review_required:
            raise ValueError("APPROVE_2_3 requires second_review_required=false")
        if self.unresolved_human_decisions:
            raise ValueError("APPROVE_2_3 requires unresolved_human_decisions=[]")
        if self.blocker_count != 0:
            raise ValueError("APPROVE_2_3 requires blocker_count=0")
        return self


class Layer22FreezeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["layer_2_2_freeze_manifest.v1"]
    dag_id: str = Field(min_length=1)
    pack_hash: str = Field(pattern=PACK_HASH_PATTERN)
    exit_decision: Literal["APPROVE_2_3"]
    review_ids: list[str] = Field(min_length=1)
    artifact_hashes: dict[str, str] = Field(min_length=1)
    frozen_artifacts: list[str] = Field(min_length=1)
    created_at: datetime


class EvidenceCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_path: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    label: str = Field(min_length=1)
    artifact_hash: str = Field(pattern=PACK_HASH_PATTERN)


class DeterministicPrecheckItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str = Field(min_length=1)
    status: Literal["pass", "fail"]
    detail: str = Field(min_length=1)


class LlmReviewPackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["llm_dag_review_pack.v1"]
    dag_id: str = Field(min_length=1)
    pack_hash: str = Field(pattern=PACK_HASH_PATTERN)
    artifact_dir: str = Field(min_length=1)
    prompt_contract_version: Literal["llm_dag_review_prompt.v1"]
    review_axes: list[str] = Field(min_length=1)
    deterministic_precheck: list[DeterministicPrecheckItem] = Field(min_length=1)
    evidence_catalog: dict[str, EvidenceCatalogEntry] = Field(min_length=1)
    artifact_hashes: dict[str, str] = Field(min_length=1)
