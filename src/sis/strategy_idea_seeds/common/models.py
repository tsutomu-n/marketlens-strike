from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


SHA256_PATTERN = r"^sha256:[a-f0-9]{64}$"
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"


class SourceLane(StrEnum):
    TECHNICAL = "TECHNICAL"


class SeedStatus(StrEnum):
    UNVERIFIED_SEED = "UNVERIFIED_SEED"


class DataReadiness(StrEnum):
    HISTORICAL_SOURCE = "HISTORICAL_SOURCE"
    DATA_REQUIRED = "DATA_REQUIRED"


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class CaptureArchetype(StrEnum):
    CONTINUATION = "CONTINUATION"
    REVERSAL = "REVERSAL"


class SeedBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backtest_evaluated: Literal[False] = False
    execution_evaluated: Literal[False] = False
    cost_evaluated: Literal[False] = False
    profit_claimed: Literal[False] = False
    auto_shortlisted: Literal[False] = False
    permits_candidate_export: Literal[False] = False
    permits_paper_candidate: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False


class SeedProducer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    producer_id: str = Field(pattern=ID_PATTERN)
    version: str = Field(min_length=1)
    canonicalization_version: Literal["seed-domain-canonicalization-v1"] = (
        "seed-domain-canonicalization-v1"
    )


class SeedLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_seed_ids: list[str] = Field(default_factory=list)
    generation_depth: int = Field(default=0, ge=0)
    mutation_operators: list[str] = Field(default_factory=list)


class SeedPayloadReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["TECHNICAL"] = "TECHNICAL"
    schema_version: Literal["strategy_idea_seed_technical_payload.v1"] = (
        "strategy_idea_seed_technical_payload.v1"
    )
    path: Literal["technical/technical_payloads.jsonl"] = "technical/technical_payloads.jsonl"
    sha256: str = Field(pattern=SHA256_PATTERN)
    record_key: str = Field(pattern=ID_PATTERN)


class RequiredSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(pattern=ID_PATTERN)
    capability: str
    requirement_status: Literal["AVAILABLE", "DATA_REQUIRED"]
    reason_codes: list[str] = Field(default_factory=list)


class ProfitIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mechanism_class: str = Field(min_length=1)
    capture_archetype: CaptureArchetype
    path_archetype: str = Field(min_length=1)
    direction_hint: Direction
    horizon_hint: str = Field(min_length=1)
    affected_actor_or_constraint: str = Field(min_length=1)
    observable_proxies: list[str] = Field(min_length=1)
    hypothesized_persistence: str = Field(min_length=1)
    alternative_explanations: list[str] = Field(min_length=1)


class StrategyIdeaSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed.v1"] = "strategy_idea_seed.v1"
    seed_record_id: str = Field(pattern=ID_PATTERN)
    created_at: datetime
    producer: SeedProducer
    source_lane: Literal[SourceLane.TECHNICAL] = SourceLane.TECHNICAL
    status: Literal[SeedStatus.UNVERIFIED_SEED] = SeedStatus.UNVERIFIED_SEED
    data_readiness: DataReadiness
    title: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    profit_intent: ProfitIntent
    required_sources: list[RequiredSource] = Field(min_length=1)
    known_gaps: list[str]
    falsification_question: str = Field(min_length=1)
    next_research_question: str = Field(min_length=1)
    lineage: SeedLineage = Field(default_factory=SeedLineage)
    payload: SeedPayloadReference
    provenance_signature: str = Field(pattern=SHA256_PATTERN)
    boundary: SeedBoundary = Field(default_factory=SeedBoundary)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        timestamp = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return (
            timestamp.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )


class StrategyIdeaSeedSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed_set.v1"] = "strategy_idea_seed_set.v1"
    created_at: datetime
    producer: SeedProducer
    seed_count: int = Field(ge=0)
    data_required_count: int = Field(ge=0)
    semantic_hash: str = Field(pattern=SHA256_PATTERN)
    seeds: list[StrategyIdeaSeed]
    boundary: SeedBoundary = Field(default_factory=SeedBoundary)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        timestamp = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return (
            timestamp.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    @model_validator(mode="after")
    def validate_counts_and_ids(self) -> StrategyIdeaSeedSet:
        if self.seed_count != len(self.seeds):
            raise ValueError("seed_count must match seeds")
        expected_required = sum(
            seed.data_readiness is DataReadiness.DATA_REQUIRED for seed in self.seeds
        )
        if self.data_required_count != expected_required:
            raise ValueError("data_required_count must match DATA_REQUIRED seeds")
        ids = [seed.seed_record_id for seed in self.seeds]
        if len(ids) != len(set(ids)):
            raise ValueError("seed_record_id values must be unique")
        return self


class SeedInputReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_key: str = Field(pattern=ID_PATTERN)
    path: str
    sha256: str = Field(pattern=SHA256_PATTERN)


class SeedArtifactReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: str = Field(pattern=ID_PATTERN)
    path: str
    sha256: str = Field(pattern=SHA256_PATTERN)
    record_count: int | None = Field(default=None, ge=0)


class SeedRunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed_run_manifest.v1"] = (
        "strategy_idea_seed_run_manifest.v1"
    )
    run_id: str = Field(pattern=ID_PATTERN)
    created_at: datetime
    producer: SeedProducer
    git_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    inputs: list[SeedInputReference]
    configs: list[SeedInputReference]
    attempt_count: int = Field(ge=0)
    seed_count: int = Field(ge=0)
    data_required_count: int = Field(ge=0)
    next_cursor: int | None = Field(default=None, ge=0)
    reason_counts: dict[str, int]
    artifacts: list[SeedArtifactReference]
    boundary_summary: SeedBoundary = Field(default_factory=SeedBoundary)
    known_gaps: list[str]
    run_status: Literal["pass"] = "pass"

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        timestamp = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return (
            timestamp.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
