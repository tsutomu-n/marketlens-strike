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
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


PROPOSAL_SCHEMA_VERSION = "strategy_input_contract_update_proposal.v1"
REVIEW_SCHEMA_VERSION = "strategy_input_contract_update_review.v1"


class StrategyInputFeedbackProposalStatus(StrEnum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    NEEDS_SOURCE_CONTRACT_CONTEXT = "NEEDS_SOURCE_CONTRACT_CONTEXT"
    NO_CHANGES_RECOMMENDED = "NO_CHANGES_RECOMMENDED"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class StrategyInputFeedbackReviewDecision(StrEnum):
    APPROVE_FOR_MANUAL_CONTRACT_UPDATE = "APPROVE_FOR_MANUAL_CONTRACT_UPDATE"
    REJECT = "REJECT"
    HOLD = "HOLD"
    NEEDS_FIX = "NEEDS_FIX"


class StrategyInputFeedbackSourceKind(StrEnum):
    STRATEGY_INPUT_CONTRACT = "strategy_input_contract"
    RUNTIME_OBSERVATION = "runtime_observation"
    LEARNING_EVENT = "learning_event"


class StrategyInputFeedbackTargetSection(StrEnum):
    SOURCE_VALIDATION_EXPECTATIONS = "source_validation_expectations"
    KNOWN_GAPS = "known_gaps"
    EXECUTION_REALITY = "execution_reality"
    STRATEGY_SCOPE = "strategy_scope"
    RISK_ASSUMPTION = "risk_assumption"
    MANUAL_NOTE = "manual_note"


class StrategyInputFeedbackBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    permits_wallet: Literal[False] = False
    permits_signing: Literal[False] = False
    permits_exchange_write: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    auto_applied: Literal[False] = False
    direct_contract_edit_allowed: Literal[False] = False


class StrategyInputFeedbackSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_kind: StrategyInputFeedbackSourceKind
    path: str
    sha256: str
    schema_version: str

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

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("schema_version must not be empty")
        return stripped


class StrategyInputFeedbackProposedChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_id: str
    target_section: StrategyInputFeedbackTargetSection
    recommendation: str
    evidence_summary: str
    source_reason: str
    requires_human_review: Literal[True] = True

    @field_validator("change_id")
    @classmethod
    def validate_change_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("change_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("recommendation", "evidence_summary", "source_reason")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped


class StrategyInputContractUpdateProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_input_contract_update_proposal.v1"] = PROPOSAL_SCHEMA_VERSION
    proposal_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    status: StrategyInputFeedbackProposalStatus
    source_artifacts: list[StrategyInputFeedbackSourceArtifact] = Field(min_length=1)
    proposed_changes: list[StrategyInputFeedbackProposedChange] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    requires_human_review: Literal[True] = True
    auto_applied: Literal[False] = False
    direct_contract_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)
    feedback_boundary: StrategyInputFeedbackBoundary = Field(
        default_factory=StrategyInputFeedbackBoundary
    )

    @field_validator("proposal_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("blocked_reasons")
    @classmethod
    def validate_blocked_reasons(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("blocked_reasons must not contain empty items")
        return cleaned

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_status_shape(self) -> StrategyInputContractUpdateProposal:
        if self.status is StrategyInputFeedbackProposalStatus.READY_FOR_HUMAN_REVIEW:
            if not self.proposed_changes:
                raise ValueError("READY_FOR_HUMAN_REVIEW requires proposed_changes")
            if not any(
                source.artifact_kind is StrategyInputFeedbackSourceKind.STRATEGY_INPUT_CONTRACT
                for source in self.source_artifacts
            ):
                raise ValueError("READY_FOR_HUMAN_REVIEW requires source contract context")
        if self.status is StrategyInputFeedbackProposalStatus.BLOCKED_BOUNDARY_VIOLATION:
            if not self.blocked_reasons:
                raise ValueError("BLOCKED_BOUNDARY_VIOLATION requires blocked_reasons")
        if self.status is StrategyInputFeedbackProposalStatus.NO_CHANGES_RECOMMENDED:
            if self.proposed_changes:
                raise ValueError("NO_CHANGES_RECOMMENDED must not include proposed_changes")
        return self


class StrategyInputFeedbackSourceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_path: str
    proposal_sha256: str
    proposal_id: str
    proposal_status: StrategyInputFeedbackProposalStatus
    proposed_change_ids: list[str]
    proposed_change_count: int = Field(ge=0)
    auto_applied: Literal[False] = False
    direct_contract_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False

    @field_validator("proposal_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("proposal_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("proposal_sha256 must match sha256:<64 lowercase hex>")
        return value

    @field_validator("proposal_id")
    @classmethod
    def validate_proposal_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("proposal_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("proposed_change_ids")
    @classmethod
    def validate_change_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("proposed_change_ids must not contain empty items")
        if any(not REVIEW_ID_PATTERN.fullmatch(item) for item in cleaned):
            raise ValueError("proposed_change_ids must match id pattern")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("proposed_change_ids must be unique")
        return cleaned

    @model_validator(mode="after")
    def validate_change_count(self) -> StrategyInputFeedbackSourceProposal:
        if self.proposed_change_count != len(self.proposed_change_ids):
            raise ValueError("proposed_change_count must equal proposed_change_ids length")
        return self


class StrategyInputContractUpdateReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_input_contract_update_review.v1"] = REVIEW_SCHEMA_VERSION
    review_id: str
    proposal_id: str
    strategy_id: str
    reviewed_at: datetime
    producer: StageProducer
    reviewer: str
    decision: StrategyInputFeedbackReviewDecision
    rationale: str
    approved_change_ids: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    source_proposal: StrategyInputFeedbackSourceProposal
    manual_contract_update_input_allowed: bool
    requires_human_contract_update: Literal[True] = True
    auto_applied: Literal[False] = False
    direct_contract_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)
    feedback_boundary: StrategyInputFeedbackBoundary = Field(
        default_factory=StrategyInputFeedbackBoundary
    )

    @field_validator("review_id", "proposal_id", "strategy_id")
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

    @field_validator("approved_change_ids", "required_actions")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("string lists must not contain empty items")
        return cleaned

    @field_serializer("reviewed_at")
    def serialize_reviewed_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_review_contract(self) -> StrategyInputContractUpdateReview:
        if self.proposal_id != self.source_proposal.proposal_id:
            raise ValueError("proposal_id must match source_proposal.proposal_id")
        unknown = sorted(
            set(self.approved_change_ids) - set(self.source_proposal.proposed_change_ids)
        )
        if unknown:
            raise ValueError("approved_change_ids not found in proposal: " + ", ".join(unknown))
        if self.decision is StrategyInputFeedbackReviewDecision.NEEDS_FIX:
            if not self.required_actions:
                raise ValueError("NEEDS_FIX requires at least one required action")
        if self.decision is StrategyInputFeedbackReviewDecision.APPROVE_FOR_MANUAL_CONTRACT_UPDATE:
            if (
                self.source_proposal.proposal_status
                is not StrategyInputFeedbackProposalStatus.READY_FOR_HUMAN_REVIEW
            ):
                raise ValueError(
                    "APPROVE_FOR_MANUAL_CONTRACT_UPDATE requires READY_FOR_HUMAN_REVIEW proposal"
                )
            if not self.approved_change_ids:
                raise ValueError("APPROVE_FOR_MANUAL_CONTRACT_UPDATE requires approved changes")
            if not self.manual_contract_update_input_allowed:
                raise ValueError(
                    "APPROVE_FOR_MANUAL_CONTRACT_UPDATE requires manual_contract_update_input_allowed"
                )
        else:
            if (
                self.decision
                in {
                    StrategyInputFeedbackReviewDecision.REJECT,
                    StrategyInputFeedbackReviewDecision.HOLD,
                }
                and self.approved_change_ids
            ):
                raise ValueError("REJECT/HOLD must not include approved_change_ids")
            if self.manual_contract_update_input_allowed:
                raise ValueError("manual_contract_update_input_allowed requires approval decision")
        return self
