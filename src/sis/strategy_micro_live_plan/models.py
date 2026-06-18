from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageCondition, StageProducer, StageSafetyBoundary


MICRO_LIVE_PLAN_SCHEMA_VERSION = "strategy_micro_live_plan.v1"


class MicroLivePlanStatus(StrEnum):
    READY_FOR_HUMAN_MICRO_LIVE_REVIEW = "READY_FOR_HUMAN_MICRO_LIVE_REVIEW"
    NEEDS_STAGE_DECISION = "NEEDS_STAGE_DECISION"
    NEEDS_DRIFT_REVIEW = "NEEDS_DRIFT_REVIEW"
    NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"
    NEEDS_RISK_LIMITS = "NEEDS_RISK_LIMITS"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class MicroLiveSourceArtifact(BaseModel):
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


class MicroLiveRiskLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_order_notional_usd: float = Field(gt=0)
    max_position_notional_usd: float = Field(gt=0)
    max_daily_loss_usd: float = Field(gt=0)
    max_total_loss_usd: float = Field(gt=0)
    max_open_positions: int = Field(ge=1)
    allowed_symbols: list[str] = Field(min_length=1)
    session_window: str

    @field_validator("allowed_symbols")
    @classmethod
    def validate_allowed_symbols(cls, value: list[str]) -> list[str]:
        cleaned = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if not cleaned:
            raise ValueError("allowed_symbols must not be empty")
        return list(dict.fromkeys(cleaned))

    @field_validator("session_window")
    @classmethod
    def validate_session_window(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("session_window must not be empty")
        return stripped


class MicroLiveMonitoringPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str
    cadence: str
    schedule_cancel_procedure: str
    kill_switch_procedure: str

    @field_validator("owner", "cadence", "schedule_cancel_procedure", "kill_switch_procedure")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("monitoring fields must not be empty")
        return stripped


class MicroLivePolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_path: str | None = None
    policy_hash: str | None = None
    enabled: bool
    venue: str
    max_notional_usd: float
    max_daily_loss_usd: float
    max_open_positions: int
    max_leverage: float
    allowed_symbols: list[str]
    schedule_cancel_deadline_seconds_after_now: int
    close_require_reduce_only: bool

    @field_validator("policy_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_repo_relative_posix_path(value)

    @field_validator("policy_hash")
    @classmethod
    def validate_optional_hash(cls, value: str | None) -> str | None:
        if value is not None and not SHA256_PATTERN.fullmatch(value):
            raise ValueError("policy_hash must match sha256:<64 lowercase hex>")
        return value


class StrategyMicroLivePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_micro_live_plan.v1"] = MICRO_LIVE_PLAN_SCHEMA_VERSION
    plan_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    plan_status: MicroLivePlanStatus
    stage_decision_status: str | None
    drift_review_status: str | None
    drift_recommended_action: str | None
    human_approval_present: bool
    source_artifacts: list[MicroLiveSourceArtifact]
    risk_limits: MicroLiveRiskLimits
    monitoring_plan: MicroLiveMonitoringPlan
    micro_live_policy_snapshot: MicroLivePolicySnapshot | None = None
    passed_conditions: list[StageCondition]
    failed_conditions: list[StageCondition]
    warning_conditions: list[StageCondition]
    required_human_review: Literal[True] = True
    micro_live_execution_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("plan_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
