from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import CANDIDATE_PROTOCOL_MANIFEST_SCHEMA_VERSION


class CandidateProtocolMode(StrEnum):
    VERIFICATION_THROUGHPUT = "verification_throughput"
    RISK_TAKER_SPRINT = "risk_taker_sprint"


class CandidateGeneratorType(StrEnum):
    CLASSICAL_RULE = "classical_rule"
    GRAMMAR_BASED = "grammar_based"
    LIMITED_RANDOM = "limited_random"
    LIGHT_GA = "light_ga"
    RANKING_OR_NO_TRADE_FILTER = "ranking_or_no_trade_filter"


class CandidateProtocolFamily(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str
    hypothesis: str
    generator_type: CandidateGeneratorType

    @field_validator("family_id")
    @classmethod
    def validate_family_id(cls, value: str) -> str:
        return _validate_id(value, label="family_id")

    @field_validator("hypothesis")
    @classmethod
    def validate_hypothesis(cls, value: str) -> str:
        return _validate_non_empty(value, label="hypothesis")


class SealedHoldoutDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    window_id: str
    start: datetime
    end: datetime
    peek_policy: str

    @field_validator("window_id")
    @classmethod
    def validate_window_id(cls, value: str) -> str:
        return _validate_id(value, label="window_id")

    @field_validator("peek_policy")
    @classmethod
    def validate_peek_policy(cls, value: str) -> str:
        return _validate_non_empty(value, label="peek_policy")

    @field_validator("start", "end", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("sealed_holdout_definition timestamp", value)

    @field_serializer("start", "end")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_order(self) -> SealedHoldoutDefinition:
        if self.start > self.end:
            raise ValueError("sealed_holdout_definition.start must be before or equal to end")
        return self


class FamilyEventCountPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_event_count_default: int | None = Field(default=None, ge=0)
    insufficient_data_state: Literal["INCONCLUSIVE_DATA", "RESEARCH_ONLY"]


class SourceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    schema_version: str
    required: bool

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        return _validate_id(value, label="source_id")

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        return _validate_non_empty(value, label="schema_version")


class CandidateProtocolManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["candidate_protocol_manifest.v1"] = (
        CANDIDATE_PROTOCOL_MANIFEST_SCHEMA_VERSION
    )
    protocol_id: str
    mode: CandidateProtocolMode
    mode_isolation: bool = False
    created_at: datetime
    target_market: str
    target_venue_family: str
    families: list[CandidateProtocolFamily] = Field(min_length=1)
    parameter_spaces: dict[str, dict[str, Any]]
    objective: dict[str, Any]
    exclusion_rules: list[str] = Field(min_length=1)
    sealed_holdout_definition: SealedHoldoutDefinition
    family_event_count_policy: dict[str, FamilyEventCountPolicy]
    source_requirements: list[SourceRequirement] = Field(min_length=1)
    venue_execution_constraints: dict[str, Any]
    llm_policy: dict[str, Any]
    permits_actual_cash: Literal[False] = False
    permits_live_order: Literal[False] = False
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "actual_cash": False,
            "permits_live_order": False,
            "live_order_submitted": False,
            "production_exchange_write_used": False,
        }
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_validator("protocol_id")
    @classmethod
    def validate_protocol_id(cls, value: str) -> str:
        return _validate_id(value, label="protocol_id")

    @field_validator("target_market", "target_venue_family")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("exclusion_rules")
    @classmethod
    def validate_exclusion_rules(cls, value: list[str]) -> list[str]:
        return [_validate_non_empty(item, label="exclusion_rules item") for item in value]

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_protocol_shape(self) -> CandidateProtocolManifest:
        family_ids = {family.family_id for family in self.families}
        missing_parameter_spaces = sorted(family_ids - set(self.parameter_spaces))
        if missing_parameter_spaces:
            raise ValueError(
                "parameter_spaces missing family ids: " + ", ".join(missing_parameter_spaces)
            )
        missing_event_policies = sorted(family_ids - set(self.family_event_count_policy))
        if missing_event_policies:
            raise ValueError(
                "family_event_count_policy missing family ids: " + ", ".join(missing_event_policies)
            )
        if self.mode is CandidateProtocolMode.RISK_TAKER_SPRINT and self.mode_isolation is not True:
            raise ValueError("risk_taker_sprint requires mode_isolation=true")
        expected_boundary = {
            "actual_cash": False,
            "permits_live_order": False,
            "live_order_submitted": False,
            "production_exchange_write_used": False,
        }
        if self.boundary != expected_boundary:
            raise ValueError("boundary must preserve false actual_cash/live/exchange-write fields")
        if self.llm_policy.get("approval_allowed") is not False:
            raise ValueError("llm_policy.approval_allowed must be false")
        return self


def _validate_id(value: str, *, label: str) -> str:
    stripped = value.strip()
    if not ID_PATTERN.fullmatch(stripped):
        raise ValueError(f"{label} must match ^[A-Za-z0-9][A-Za-z0-9._-]{{0,127}}$")
    return stripped


def _validate_non_empty(value: str, *, label: str = "value") -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} must not be empty")
    return stripped
