from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.edge_scorer import CryptoPerpEdgeScore
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.features import CryptoPerpFeaturePack
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.source_availability import CryptoPerpSourceAvailability


BACKTEST_CANDIDATE_PACK_SCHEMA_VERSION = "crypto_perp_backtest_candidate_pack.v1"
BACKTEST_CANDIDATE_PACK_PRODUCER = "crypto-perp-backtest-candidate-pack"
BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES = (
    "signal_rows.jsonl",
    "data_availability_ledger.json",
    "execution_assumptions.json",
    "tournament_rows_v2.json",
    "bias_guard.json",
    "no_lookahead_report.json",
    "backtest_result.json",
    "stress_result.json",
    "regime_split_result.json",
    "rolling_stability_result.json",
    "decision.json",
    "decision.md",
)
BacktestCandidateDecisionName = Literal[
    "BACKTEST_REJECT",
    "BACKTEST_REVISE",
    "BACKTEST_COLLECT_MORE_DATA",
    "BACKTEST_CANDIDATE_HOLD",
]
EvidenceGradeLevel = Literal[
    "incomplete_local_artifact",
    "recomputed_minimal_simulated_estimate",
    "local_simulated_estimate",
]
EvidenceOverallGrade = Literal[
    "insufficient_source_for_local_simulation",
    "local_simulation_with_recomputed_minimal_artifacts",
    "local_simulation_from_existing_artifacts",
]


class CryptoPerpBacktestCandidatePackEvidenceGradeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    overall_grade: EvidenceOverallGrade
    strongest_evidence_level: EvidenceGradeLevel
    basis: Literal["timestamp_safe_local_simulation"]
    actual_cash_used: Literal[False]
    profit_proven: Literal[False]
    permits_live_order: Literal[False]
    event_count: int = Field(ge=0)
    simulated_trade_count: int = Field(ge=0)
    critical_missing_count: int = Field(ge=0)
    future_signal_source_count: int = Field(ge=0)
    artifact_origin_counts: dict[str, int] = Field(default_factory=dict)
    source_available_counts: dict[str, int] = Field(default_factory=dict)
    source_missing_counts: dict[str, int] = Field(default_factory=dict)
    recomputed_minimal_artifact_count: int = Field(ge=0)
    existing_artifact_only: bool
    known_limits: list[str]


class CryptoPerpBacktestCandidatePackDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_backtest_candidate_pack.v1"] = (
        BACKTEST_CANDIDATE_PACK_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    pack_id: str
    decision: BacktestCandidateDecisionName
    reason_codes: list[str]
    event_count: int = Field(ge=0)
    outcome_count: int = Field(ge=0)
    artifact_paths: dict[str, str]
    summary: dict[str, Any]
    evidence_grade_summary: CryptoPerpBacktestCandidatePackEvidenceGradeSummary | None = None
    non_goal_flags: dict[str, bool]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class BacktestCandidatePackResult:
    paths: dict[str, Path]
    decision: CryptoPerpBacktestCandidatePackDecision


@dataclass(frozen=True)
class _EventOutcomePair:
    event_path: Path
    event: CryptoPerpEvent
    outcome_path: Path
    outcome: CryptoPerpOutcome


@dataclass(frozen=True)
class _ArtifactOrigin:
    origin: Literal["existing", "recomputed_minimal"]
    path: str | None
    note: str


@dataclass(frozen=True)
class _PerEventArtifacts:
    source_availability: CryptoPerpSourceAvailability
    source_origin: _ArtifactOrigin
    feature_pack: CryptoPerpFeaturePack
    feature_origin: _ArtifactOrigin
    edge_score: CryptoPerpEdgeScore
    edge_origin: _ArtifactOrigin
