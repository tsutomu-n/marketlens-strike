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


POLICY_SCHEMA_VERSION = "strategy_stage_policy.v1"
POLICY_VALIDATION_SCHEMA_VERSION = "strategy_stage_policy_validation.v1"
DECISION_SCHEMA_VERSION = "strategy_stage_decision.v1"


class StageName(StrEnum):
    PAPER_SMOKE = "paper_smoke"
    NORMAL_PAPER_OBSERVATION = "normal_paper_observation"
    DRIFT_REVIEW = "drift_review"
    MICRO_LIVE_PLAN = "micro_live_plan"


class StagePolicyValidationStatus(StrEnum):
    PASS = "PASS"
    INVALID_INPUT = "INVALID_INPUT"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class StageDecisionStatus(StrEnum):
    BLOCKED = "BLOCKED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    READY_FOR_PAPER_SMOKE_PLAN = "READY_FOR_PAPER_SMOKE_PLAN"
    READY_FOR_NORMAL_PAPER_OBSERVATION = "READY_FOR_NORMAL_PAPER_OBSERVATION"
    READY_FOR_DRIFT_REVIEW = "READY_FOR_DRIFT_REVIEW"
    READY_FOR_MICRO_LIVE_PLAN = "READY_FOR_MICRO_LIVE_PLAN"


class StageProducer(BaseModel):
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


class StageSafetyBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False


class StageFixedSafety(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_source_hashes: Literal[True] = True
    require_schema_versions: Literal[True] = True
    forbid_live_order_before_micro_live_gate: Literal[True] = True
    forbid_wallet_before_micro_live_gate: Literal[True] = True
    forbid_signing_before_micro_live_gate: Literal[True] = True
    forbid_exchange_write_before_micro_live_gate: Literal[True] = True
    require_manual_override_reason: Literal[True] = True


class StageThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_fills: int | None = Field(default=None, ge=0)
    min_trading_days: int | None = Field(default=None, ge=0)
    max_no_fill_rate: float | None = Field(default=None, ge=0, le=1)
    max_slippage_bps: float | None = Field(default=None, ge=0)
    max_order_notional_usd: float | None = Field(default=None, gt=0)
    max_position_notional_usd: float | None = Field(default=None, gt=0)
    max_orders_per_day: int | None = Field(default=None, ge=0)
    stop_after_consecutive_errors: int | None = Field(default=None, ge=0)
    max_drawdown_vs_backtest_ratio: float | None = Field(default=None, gt=0)
    max_blocked_rate: float | None = Field(default=None, ge=0, le=1)
    max_consecutive_blocked: int | None = Field(default=None, ge=0)
    max_total_notional_usd: float | None = Field(default=None, gt=0)
    max_daily_loss_usd: float | None = Field(default=None, gt=0)
    max_total_loss_usd: float | None = Field(default=None, gt=0)
    max_runtime_days: int | None = Field(default=None, ge=0)
    require_manual_start: bool | None = None
    require_kill_switch: bool | None = None
    require_monitoring_plan: bool | None = None


class StrategyStagePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_stage_policy.v1"] = POLICY_SCHEMA_VERSION
    policy_id: str
    description: str
    fixed_safety: StageFixedSafety
    stages: dict[StageName, StageThresholds]
    strategy_profiles: dict[str, dict[StageName, StageThresholds]] = Field(default_factory=dict)
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("policy_id")
    @classmethod
    def validate_policy_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("policy_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("description must not be empty")
        return stripped

    @model_validator(mode="after")
    def validate_required_stages(self) -> StrategyStagePolicy:
        missing = [stage.value for stage in StageName if stage not in self.stages]
        if missing:
            raise ValueError("stages missing required stage(s): " + ", ".join(missing))
        return self


class StagePolicyValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_count: int = Field(ge=0)
    profile_count: int = Field(ge=0)
    boundary_violation_count: int = Field(ge=0)


class StrategyStagePolicyValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_stage_policy_validation.v1"] = (
        POLICY_VALIDATION_SCHEMA_VERSION
    )
    policy_id: str
    policy_path: str
    policy_hash: str
    validated_at: datetime
    producer: StageProducer
    validation_status: StagePolicyValidationStatus
    summary: StagePolicyValidationSummary
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("policy_path")
    @classmethod
    def validate_policy_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("policy_hash")
    @classmethod
    def validate_policy_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("policy_hash must match sha256:<64 lowercase hex>")
        return value

    @field_serializer("validated_at")
    def serialize_validated_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )


class StageSourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: str
    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("artifact_key")
    @classmethod
    def validate_artifact_key(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact_key must not be empty")
        return stripped

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


class StageCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str
    passed: bool
    observed: str
    required: str
    severity: Literal["error", "warning"] = "error"

    @field_validator("condition_id", "observed", "required")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("condition fields must not be empty")
        return stripped


class StagePaperRequirementGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed: int = Field(ge=0)
    required: int = Field(ge=0)
    remaining: int = Field(ge=0)
    met: bool


class StagePaperEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_status_present: bool
    smoke_pass_present: bool | None = None
    smoke_pass_counts_as_normal_pass: bool | None = None
    normal_thresholds_met: bool | None = None
    latest_normal_session_id: str | None = None
    normal_fills: StagePaperRequirementGap | None = None
    normal_trading_days: StagePaperRequirementGap | None = None

    @field_validator("latest_normal_session_id")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class StrategyStageDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_stage_decision.v1"] = DECISION_SCHEMA_VERSION
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    policy_id: str
    policy_hash: str
    selected_stage: StageName
    selected_profile: str
    decision: StageDecisionStatus
    source_artifacts: list[StageSourceArtifact]
    passed_conditions: list[StageCondition]
    failed_conditions: list[StageCondition]
    warning_conditions: list[StageCondition]
    manual_overrides: list[str]
    paper_evidence_summary: StagePaperEvidenceSummary | None = None
    override_reason: str | None = None
    reviewer: str | None = None
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("strategy_id", "policy_id", "selected_profile")
    @classmethod
    def validate_id_text(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("policy_hash")
    @classmethod
    def validate_policy_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("policy_hash must match sha256:<64 lowercase hex>")
        return value

    @field_validator("manual_overrides")
    @classmethod
    def validate_manual_overrides(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("manual_overrides must not contain empty items")
        return cleaned

    @field_validator("override_reason", "reviewer")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional text fields must not be empty")
        return value.strip() if value is not None else None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
