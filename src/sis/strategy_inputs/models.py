from __future__ import annotations

import re
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

from sis.strategy_review.manifest import SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path


ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
INPUT_CONTRACT_SCHEMA_VERSION = "strategy_input_contract.v1"
INPUT_VALIDATION_SCHEMA_VERSION = "strategy_input_contract_validation.v1"
STRATEGY_IDEA_SCHEMA_VERSION = "strategy_idea.v1"
INTAKE_DECISION_SCHEMA_VERSION = "strategy_intake_decision.v1"


class InputSourceType(StrEnum):
    RAW_MARKET_DATA = "raw_market_data"
    DERIVED_FEATURES = "derived_features"
    TEMPORAL_AVAILABILITY = "temporal_availability"
    EXECUTION_REALITY = "execution_reality"
    UNIVERSE = "universe"
    EXTERNAL_EVENT = "external_event"
    RISK_ACCOUNT = "risk_account"
    RUNTIME_OBSERVATION = "runtime_observation"
    FEEDBACK_METADATA = "feedback_metadata"
    MANUAL_NOTE = "manual_note"


class InputRevisionPolicy(StrEnum):
    APPEND_ONLY = "append_only"
    SNAPSHOT_IMMUTABLE = "snapshot_immutable"
    REVISION_TRACKED = "revision_tracked"


class InputSurvivorshipPolicy(StrEnum):
    POINT_IN_TIME = "point_in_time"
    CURRENT_CONSTITUENTS_NOT_ALLOWED = "current_constituents_not_allowed"
    NOT_APPLICABLE = "not_applicable"


class InputValidationStatus(StrEnum):
    PASS = "PASS"
    NEEDS_FIX = "NEEDS_FIX"
    INVALID_INPUT = "INVALID_INPUT"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class SourceValidationStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"
    BLOCKED = "blocked"


class IdeaIntakeDecision(StrEnum):
    REJECT = "REJECT"
    NEEDS_SPEC = "NEEDS_SPEC"
    NEEDS_DATA_CHECK = "NEEDS_DATA_CHECK"
    NEEDS_RISK_SPEC = "NEEDS_RISK_SPEC"
    READY_FOR_AUTHORING_DRAFT = "READY_FOR_AUTHORING_DRAFT"


class StrategyInputBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False


class ProducerInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal["sis"] = "sis"
    command: str

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("command must not be empty")
        return stripped


class StrategyScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_family: str
    instruments: list[str] = Field(min_length=1)
    timeframe: str
    intended_use: Literal["research_backtest_only", "paper_observation_research_only"]

    @field_validator("strategy_family", "timeframe")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("instruments")
    @classmethod
    def validate_instruments(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("instruments must not contain empty items")
        return cleaned


class ExecutionReality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    includes_fills: bool = False
    includes_slippage: bool = False
    includes_latency: bool = False
    assumed_order_type: str

    @field_validator("assumed_order_type")
    @classmethod
    def validate_assumed_order_type(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("assumed_order_type must not be empty")
        return stripped


class SourceValidationExpectations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_columns: list[str] = Field(default_factory=list)
    timestamp_column: str | None = None
    max_allowed_timestamp: datetime | None = None
    available_at_column: str | None = None
    available_at_column_required: bool = False

    @field_validator("required_columns")
    @classmethod
    def validate_required_columns(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("required_columns must not contain empty items")
        return list(dict.fromkeys(cleaned))

    @field_validator("timestamp_column", "available_at_column")
    @classmethod
    def validate_optional_column(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("column names must not be empty")
        return stripped

    @field_serializer("max_allowed_timestamp")
    def serialize_max_allowed_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_expectations(self) -> SourceValidationExpectations:
        if self.max_allowed_timestamp is not None and self.timestamp_column is None:
            raise ValueError("max_allowed_timestamp requires timestamp_column")
        if self.available_at_column_required and self.available_at_column is None:
            raise ValueError("available_at_column_required requires available_at_column")
        return self


class StrategyInputSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_type: InputSourceType
    path: str
    required: bool = True
    declared_sha256: str | None = None
    schema_version: str | None = None
    generated_at: datetime
    available_at: datetime
    revision_policy: InputRevisionPolicy
    survivorship_policy: InputSurvivorshipPolicy
    execution_reality: ExecutionReality
    validation_expectations: SourceValidationExpectations | None = None

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if not ID_PATTERN.fullmatch(value):
            raise ValueError("source_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("declared_sha256")
    @classmethod
    def validate_declared_sha256(cls, value: str | None) -> str | None:
        if value is not None and not SHA256_PATTERN.fullmatch(value):
            raise ValueError("declared_sha256 must match sha256:<64 lowercase hex>")
        return value

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("schema_version must not be empty")
        return value.strip() if value is not None else None

    @field_serializer("generated_at", "available_at")
    def serialize_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_source_contract(self) -> StrategyInputSource:
        if self.required and self.declared_sha256 is None:
            raise ValueError("required source requires declared_sha256")
        return self


class StrategyInputContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_input_contract.v1"] = INPUT_CONTRACT_SCHEMA_VERSION
    contract_id: str
    created_at: datetime
    producer: ProducerInfo
    strategy_scope: StrategyScope
    sources: list[StrategyInputSource] = Field(min_length=1)
    known_gaps: list[str] = Field(default_factory=list)
    boundary: StrategyInputBoundary = Field(default_factory=StrategyInputBoundary)

    @field_validator("contract_id")
    @classmethod
    def validate_contract_id(cls, value: str) -> str:
        if not ID_PATTERN.fullmatch(value):
            raise ValueError("contract_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("known_gaps")
    @classmethod
    def validate_known_gaps(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("known_gaps must not contain empty items")
        return cleaned

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class SourceValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    status: SourceValidationStatus
    path: str
    actual_sha256: str | None = None
    declared_sha256: str | None = None
    hash_matches: bool | None = None
    available_at_present: bool
    generated_before_available: bool | None = None
    required_columns_present: bool | None = None
    missing_columns: list[str] = Field(default_factory=list)
    timestamp_check_passed: bool | None = None
    max_observed_timestamp: str | None = None
    available_at_column_present: bool | None = None
    error: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)


class InputValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_required_count: int = Field(ge=0)
    invalid_required_count: int = Field(ge=0)
    boundary_violation_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    column_check_failure_count: int = Field(ge=0, default=0)
    timestamp_violation_count: int = Field(ge=0, default=0)


class StrategyInputContractValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_input_contract_validation.v1"] = (
        INPUT_VALIDATION_SCHEMA_VERSION
    )
    contract_id: str
    validated_at: datetime
    producer: ProducerInfo
    validation_status: InputValidationStatus
    strict: bool
    source_results: list[SourceValidationResult]
    summary: InputValidationSummary
    boundary: StrategyInputBoundary = Field(default_factory=StrategyInputBoundary)

    @field_serializer("validated_at")
    def serialize_validated_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class BaselineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    expected_to_beat: bool

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped


class RiskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_position_notional_usd: float = Field(gt=0)
    max_daily_loss_usd: float = Field(gt=0)
    kill_conditions: list[str] = Field(min_length=1)

    @field_validator("kill_conditions")
    @classmethod
    def validate_kill_conditions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("kill_conditions must not contain empty items")
        return cleaned


class ExecutionAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_type: str
    slippage_model: str

    @field_validator("order_type", "slippage_model")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class AuthoringIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: Literal["strategy_authoring_draft"]
    auto_generate_spec: Literal[False] = False


class StrategyIdea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea.v1"] = STRATEGY_IDEA_SCHEMA_VERSION
    idea_id: str
    created_at: datetime
    title: str
    hypothesis: str
    mechanism: str
    timeframe: str
    instruments: list[str] = Field(min_length=1)
    required_input_contract_ids: list[str] = Field(min_length=1)
    baseline: BaselineSpec
    invalidation: list[str] = Field(min_length=1)
    risk: RiskSpec
    execution_assumptions: ExecutionAssumptions
    authoring_intent: AuthoringIntent
    boundary: StrategyInputBoundary = Field(default_factory=StrategyInputBoundary)

    @field_validator("idea_id")
    @classmethod
    def validate_idea_id(cls, value: str) -> str:
        if not ID_PATTERN.fullmatch(value):
            raise ValueError("idea_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("title", "hypothesis", "mechanism", "timeframe")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("instruments", "required_input_contract_ids", "invalidation")
    @classmethod
    def validate_text_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("list must not contain empty items")
        return cleaned

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class InputContractRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: str
    validation_status: InputValidationStatus


class IntakeDecisionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_hypothesis: bool
    missing_baseline: bool
    missing_invalidation: bool
    missing_risk: bool
    missing_required_inputs: bool
    boundary_violation_count: int = Field(ge=0)


class StrategyIntakeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_intake_decision.v1"] = INTAKE_DECISION_SCHEMA_VERSION
    idea_id: str
    decided_at: datetime
    producer: ProducerInfo
    decision: IdeaIntakeDecision
    required_actions: list[str]
    input_contract_refs: list[InputContractRef]
    summary: IntakeDecisionSummary
    boundary: StrategyInputBoundary = Field(default_factory=StrategyInputBoundary)

    @field_serializer("decided_at")
    def serialize_decided_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_ready_shape(self) -> StrategyIntakeDecision:
        if self.decision is IdeaIntakeDecision.READY_FOR_AUTHORING_DRAFT:
            if self.required_actions:
                raise ValueError("READY_FOR_AUTHORING_DRAFT requires no required_actions")
            if self.summary.boundary_violation_count:
                raise ValueError("READY_FOR_AUTHORING_DRAFT requires zero boundary violations")
            if any(
                (
                    self.summary.missing_hypothesis,
                    self.summary.missing_baseline,
                    self.summary.missing_invalidation,
                    self.summary.missing_risk,
                    self.summary.missing_required_inputs,
                )
            ):
                raise ValueError("READY_FOR_AUTHORING_DRAFT requires no missing spec fields")
            if any(
                ref.validation_status is not InputValidationStatus.PASS
                for ref in self.input_contract_refs
            ):
                raise ValueError("READY_FOR_AUTHORING_DRAFT requires PASS input contracts")
        return self
