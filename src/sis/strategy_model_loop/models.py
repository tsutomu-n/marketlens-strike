from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


MODEL_RUN_SCHEMA_VERSION = "strategy_model_run.v1"
OPTIMIZER_TRIAL_LEDGER_SCHEMA_VERSION = "strategy_optimizer_trial_ledger.v1"


class ModelOutputRoute(StrEnum):
    IDEA_INTAKE_ONLY = "IDEA_INTAKE_ONLY"
    REVISION_REQUEST_ONLY = "REVISION_REQUEST_ONLY"


class OptimizerTrialStatus(StrEnum):
    COMPLETE = "complete"
    FAILED = "failed"
    PRUNED = "pruned"
    RUNNING = "running"


class StrategyModelTrainingData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str

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


class StrategyOptimizerTrial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: str
    status: OptimizerTrialStatus
    parameters: dict[str, Any] = Field(default_factory=dict)
    objective_value: float | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None

    @field_validator("trial_id")
    @classmethod
    def validate_trial_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("trial_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value


class StrategyOptimizerTrialLedgerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_count: int = Field(ge=0)
    complete_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    pruned_count: int = Field(ge=0)
    running_count: int = Field(ge=0)
    success_only_reporting: Literal[False] = False


class StrategyOptimizerTrialLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_optimizer_trial_ledger.v1"] = (
        OPTIMIZER_TRIAL_LEDGER_SCHEMA_VERSION
    )
    ledger_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    search_space: dict[str, Any]
    trials: list[StrategyOptimizerTrial]
    best_trial_id: str | None = None
    holdout_result: dict[str, Any] = Field(default_factory=dict)
    summary: StrategyOptimizerTrialLedgerSummary
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    auto_applied: Literal[False] = False
    direct_spec_edit_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("ledger_id", "strategy_id")
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


class StrategyModelRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_model_run.v1"] = MODEL_RUN_SCHEMA_VERSION
    model_run_id: str
    strategy_id: str
    created_at: datetime
    producer: StageProducer
    training_data: StrategyModelTrainingData
    label_definition: str
    split: str
    seed: int | None = None
    search_space_hash: str
    optimizer_trial_ledger_path: str
    optimizer_trial_ledger_sha256: str
    best_trial_id: str | None = None
    holdout_result: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str]
    output_route: ModelOutputRoute
    auto_applied: Literal[False] = False
    direct_spec_edit_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("model_run_id", "strategy_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("label_definition", "split")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped

    @field_validator("search_space_hash", "optimizer_trial_ledger_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("hash must match sha256:<64 lowercase hex>")
        return value

    @field_validator("optimizer_trial_ledger_path")
    @classmethod
    def validate_ledger_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_serializer("created_at")
    def serialize_model_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
