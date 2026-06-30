from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import TRIAL_MULTIPLICITY_ACCOUNT_SCHEMA_VERSION
from sis.edge_candidates.protocol import CandidateProtocolMode
from sis.strategy_review.manifest import SHA256_PATTERN


class SelectionAdjustmentStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_ESTIMABLE = "NOT_ESTIMABLE"


class TrialMultiplicityAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["trial_multiplicity_account.v1"] = (
        TRIAL_MULTIPLICITY_ACCOUNT_SCHEMA_VERSION
    )
    account_id: str
    mode: CandidateProtocolMode
    candidate_count_total: int = Field(ge=0)
    candidate_count_shortlisted: int = Field(ge=0)
    family_count: int = Field(ge=0)
    family_trial_count: dict[str, int]
    parameter_grid_hashes: dict[str, str]
    effective_trial_count: int | None = Field(ge=0)
    correlation_cluster_count: int | None = Field(ge=0)
    validation_peek_count: int = Field(ge=0)
    rerank_count: int = Field(ge=0)
    sealed_test_used_for_selection: Literal[False] = False
    success_only_reporting: Literal[False] = False
    raw_p_value_count: int = Field(ge=0)
    fdr_status: SelectionAdjustmentStatus
    pbo_status: SelectionAdjustmentStatus
    dsr_status: SelectionAdjustmentStatus
    white_reality_check_status: SelectionAdjustmentStatus
    not_estimable_reasons: list[str] = Field(default_factory=list)

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("account_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("family_trial_count")
    @classmethod
    def validate_family_trial_count(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("family_trial_count must not be empty")
        for family_id, count in value.items():
            _validate_family_id(family_id)
            if count < 0:
                raise ValueError("family_trial_count values must be non-negative")
        return value

    @field_validator("parameter_grid_hashes")
    @classmethod
    def validate_parameter_grid_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("parameter_grid_hashes must not be empty")
        for family_id, digest in value.items():
            _validate_family_id(family_id)
            if not SHA256_PATTERN.fullmatch(digest):
                raise ValueError(
                    "parameter_grid_hashes values must match sha256:<64 lowercase hex>"
                )
        return value

    @field_validator("not_estimable_reasons")
    @classmethod
    def validate_reasons(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("not_estimable_reasons must not contain empty items")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("not_estimable_reasons must not contain duplicates")
        return cleaned

    @model_validator(mode="after")
    def validate_account_shape(self) -> TrialMultiplicityAccount:
        if self.candidate_count_shortlisted > self.candidate_count_total:
            raise ValueError("candidate_count_shortlisted must be <= candidate_count_total")
        if self.family_count != len(self.family_trial_count):
            raise ValueError("family_count must match family_trial_count size")
        if set(self.parameter_grid_hashes) != set(self.family_trial_count):
            raise ValueError(
                "parameter_grid_hashes must cover the same families as family_trial_count"
            )
        if sum(self.family_trial_count.values()) != self.candidate_count_total:
            raise ValueError("family_trial_count total must match candidate_count_total")
        if self.fdr_status is SelectionAdjustmentStatus.AVAILABLE and self.raw_p_value_count <= 0:
            raise ValueError("raw_p_value_count must be > 0 when fdr_status is AVAILABLE")
        if self.fdr_status is SelectionAdjustmentStatus.NOT_ESTIMABLE:
            self._require_reason("RAW_P_VALUE_MISSING_FOR_BH_FDR", "fdr_status")
        for status, reason, label in (
            (
                self.pbo_status,
                "PBO_NOT_ESTIMABLE_FOLD_OUTCOMES_MISSING",
                "pbo_status",
            ),
            (
                self.dsr_status,
                "DSR_NOT_ESTIMABLE_RETURN_DISTRIBUTION_MISSING",
                "dsr_status",
            ),
            (
                self.white_reality_check_status,
                "WHITE_REALITY_CHECK_NOT_ESTIMABLE_BOOTSTRAP_SERIES_MISSING",
                "white_reality_check_status",
            ),
        ):
            if status is SelectionAdjustmentStatus.NOT_ESTIMABLE:
                self._require_reason(reason, label)
        if self.effective_trial_count is None:
            self._require_reason("EFFECTIVE_TRIAL_COUNT_NOT_ESTIMABLE", "effective_trial_count")
        if self.correlation_cluster_count is None:
            self._require_reason(
                "CORRELATION_CLUSTER_COUNT_NOT_ESTIMABLE",
                "correlation_cluster_count",
            )
        return self

    def _require_reason(self, reason: str, label: str) -> None:
        if reason not in self.not_estimable_reasons:
            raise ValueError(f"not_estimable_reasons must include {reason} for {label}")


def _validate_family_id(value: str) -> None:
    if not ID_PATTERN.fullmatch(value):
        raise ValueError("family ids must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
