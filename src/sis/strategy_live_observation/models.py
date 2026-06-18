from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


LIVE_OBSERVATION_SCHEMA_VERSION = "strategy_live_observation_manifest.v1"


class LiveObservationIngestStatus(StrEnum):
    LIVE_OBSERVATION_INGESTED = "LIVE_OBSERVATION_INGESTED"
    BLOCKED_CANARY = "BLOCKED_CANARY"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class LiveObservationSourceArtifact(BaseModel):
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


class LiveObservationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canary_status: str
    blocked_reasons: list[str] = Field(default_factory=list)
    canonical_symbol: str | None = None
    side: str | None = None
    quantity: float | None = None
    limit_price: float | None = None
    notional_usd: float | None = None
    leverage: float | None = None
    schedule_cancel_status: str | None = None
    order_submit_status: str | None = None
    order_status: str | None = None
    cancel_status: str | None = None
    close_status: str | None = None
    actual_fill_observed: bool = False
    rejection_observed: bool = False
    cancel_observed: bool = False
    close_submitted: bool = False
    fee_usd: float | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    position_reconciliation_status: str = "not_provided"
    max_loss_breach_observed: bool = False
    account_snapshot_present: bool = False
    account_equity: float | None = None
    account_available_cash: float | None = None

    @field_validator("canary_status")
    @classmethod
    def validate_canary_status(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("canary_status must not be empty")
        return stripped


class StrategyLiveObservationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_live_observation_manifest.v1"] = (
        LIVE_OBSERVATION_SCHEMA_VERSION
    )
    strategy_id: str
    observation_id: str
    created_at: datetime
    producer: StageProducer
    ingest_status: LiveObservationIngestStatus
    source_artifacts: list[LiveObservationSourceArtifact]
    summary: LiveObservationSummary
    paper_runtime_observation_mixed: Literal[False] = False
    live_execution_submitted_by_this_command: Literal[False] = False
    scale_up_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("strategy_id", "observation_id")
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
