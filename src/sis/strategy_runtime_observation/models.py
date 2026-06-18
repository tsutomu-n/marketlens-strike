from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.strategy_stage.models import StageProducer, StageSafetyBoundary


RUNTIME_OBSERVATION_SCHEMA_VERSION = "strategy_runtime_observation_manifest.v1"


class RuntimeObservationSourceStage(StrEnum):
    PAPER_SMOKE = "paper_smoke"
    NORMAL_PAPER_OBSERVATION = "normal_paper_observation"


class RuntimeObservationIngestStatus(StrEnum):
    INGESTED = "INGESTED"
    EMPTY_LEDGER = "EMPTY_LEDGER"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class RuntimeObservationSourceArtifact(BaseModel):
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


class RuntimeObservationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ledger_entry_count: int = Field(ge=0)
    paper_order_count: int = Field(ge=0)
    paper_fill_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    no_fill_count: int = Field(ge=0)
    unique_intent_count: int = Field(ge=0)
    unique_symbol_count: int = Field(ge=0)
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    max_observed_spread_bps: float | None = None
    max_observed_quote_age_ms: int | None = Field(default=None, ge=0)
    pnl_available: bool = False
    pnl_unavailable_reason: str | None = None
    realized_pnl_usd_total: float | None = None
    gross_pnl_usd_total: float | None = None
    fee_usd_total: float | None = None
    slippage_usd_total: float | None = None
    avg_slippage_bps: float | None = None
    max_abs_slippage_bps: float | None = None
    avg_fill_price_drift_bps: float | None = None
    max_abs_fill_price_drift_bps: float | None = None
    filled_notional_usd_total: float | None = None
    block_reasons: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)
    order_lifecycle_counts: dict[str, int] = Field(default_factory=dict)

    @field_validator("pnl_unavailable_reason")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class StrategyRuntimeObservationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_runtime_observation_manifest.v1"] = (
        RUNTIME_OBSERVATION_SCHEMA_VERSION
    )
    strategy_id: str
    session_id: str
    source_stage: RuntimeObservationSourceStage
    created_at: datetime
    producer: StageProducer
    ingest_status: RuntimeObservationIngestStatus
    source_artifacts: list[RuntimeObservationSourceArtifact]
    runtime_observation_ledger_path: str
    runtime_observation_ledger_sha256: str
    summary: RuntimeObservationSummary
    includes_live_order: Literal[False] = False
    includes_wallet: Literal[False] = False
    includes_signing: Literal[False] = False
    includes_exchange_write: Literal[False] = False
    live_allowed: Literal[False] = False
    boundary: StageSafetyBoundary = Field(default_factory=StageSafetyBoundary)

    @field_validator("strategy_id")
    @classmethod
    def validate_strategy_id(cls, value: str) -> str:
        if not REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("strategy_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or "/" in stripped or "\\" in stripped or stripped in {".", ".."}:
            raise ValueError("session_id must be a single non-empty path segment")
        return stripped

    @field_validator("runtime_observation_ledger_path")
    @classmethod
    def validate_ledger_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("runtime_observation_ledger_sha256")
    @classmethod
    def validate_ledger_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError(
                "runtime_observation_ledger_sha256 must match sha256:<64 lowercase hex>"
            )
        return value

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (
            value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
