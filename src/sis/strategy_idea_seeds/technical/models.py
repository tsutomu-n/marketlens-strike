from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sis.strategy_idea_seeds.common.models import (
    CaptureArchetype,
    Direction,
    ID_PATTERN,
    SHA256_PATTERN,
)


class AttemptReasonCode(StrEnum):
    INVALID_AST = "INVALID_AST"
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_UNIT = "INVALID_UNIT"
    MISSING_DIRECTION = "MISSING_DIRECTION"
    MISSING_HORIZON = "MISSING_HORIZON"
    MISSING_OBSERVABLE_PROXY = "MISSING_OBSERVABLE_PROXY"
    MISSING_SOURCE_REQUIREMENT = "MISSING_SOURCE_REQUIREMENT"
    DUPLICATE_EXACT_ATTEMPT = "DUPLICATE_EXACT_ATTEMPT"
    PRUNED_BUDGET = "PRUNED_BUDGET"
    SEED_MATERIALIZED = "SEED_MATERIALIZED"


class TechnicalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed_technical_payload.v1"] = (
        "strategy_idea_seed_technical_payload.v1"
    )
    payload_record_id: str = Field(pattern=ID_PATTERN)
    mechanism_template_id: str = Field(pattern=ID_PATTERN)
    mechanism_status: Literal["HYPOTHESIZED_NOT_CAUSALLY_VERIFIED"] = (
        "HYPOTHESIZED_NOT_CAUSALLY_VERIFIED"
    )
    operator_ast: dict[str, Any]
    generation_axes: dict[str, str]
    parameter_values: dict[str, str | int]
    technical_exact_signature: str = Field(pattern=SHA256_PATTERN)
    technical_semantic_descriptor: dict[str, str]
    source_capability_snapshot_ref: str = Field(pattern=SHA256_PATTERN)
    authoring_compatibility: Literal["NOT_CONNECTED_METADATA_ONLY"] = "NOT_CONNECTED_METADATA_ONLY"
    payload_hash: str = Field(pattern=SHA256_PATTERN)


class GenerationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed_attempt.v1"] = "strategy_idea_seed_attempt.v1"
    attempt_id: str = Field(pattern=ID_PATTERN)
    attempt_index: int = Field(ge=0)
    mechanism_template_id: str = Field(pattern=ID_PATTERN)
    direction: Direction | None
    capture_archetype: CaptureArchetype | None
    horizon: str | None
    required_sources: list[str]
    observable_proxies: list[str]
    candidate_payload: dict[str, Any] | None
    technical_exact_signature: str | None = Field(default=None, pattern=SHA256_PATTERN)
    reason_codes: list[AttemptReasonCode] = Field(min_length=1)
    materialized_seed_id: str | None = Field(default=None, pattern=ID_PATTERN)
    duplicate_of_attempt_id: str | None = Field(default=None, pattern=ID_PATTERN)

    @field_validator("reason_codes")
    @classmethod
    def validate_terminal_reason(cls, value: list[AttemptReasonCode]) -> list[AttemptReasonCode]:
        if AttemptReasonCode.SEED_MATERIALIZED in value and len(value) != 1:
            raise ValueError("SEED_MATERIALIZED must be the only reason")
        return value


class OperatorDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(pattern=ID_PATTERN)
    arity: int = Field(ge=1)
    input_types: list[str] = Field(min_length=1)
    output_type: str = Field(min_length=1)
    unit_policy: Literal["same", "boolean"]


class OperatorCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed_operator_catalog.v1"]
    operators: list[OperatorDefinition] = Field(min_length=1)


class ThresholdDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | int | float
    value_type: str
    unit: str


class MechanismTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mechanism_template_id: str = Field(pattern=ID_PATTERN)
    mechanism_class: str
    affected_actor_or_constraint: str
    observable_proxies: list[str]
    captures: list[str | None]
    directions: list[str | None]
    horizons: list[str | None]
    lookbacks: list[int]
    thresholds: list[ThresholdDefinition]
    required_source_bundles: list[list[str]]
    primary_field: str
    primary_field_type: str
    primary_field_unit: str
    comparison_operator: str
    hypothesized_persistence: str
    alternative_explanations: list[str]
    falsification_question: str
    next_research_question: str


class MechanismPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed_mechanism_pack.v1"]
    attempt_budget: int | None = Field(default=None, ge=0)
    mechanisms: list[MechanismTemplate] = Field(min_length=1)
