from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from sis.strategy_idea_candidates.models import CandidateBoundary
from sis.strategy_inputs.models import ProducerInfo


AUTHORING_BRIDGE_SCHEMA_VERSION = "strategy_idea_candidate_authoring_bridge.v1"

BridgeStatus = Literal[
    "BRIDGED_TECHNICAL_ONLY",
    "BLOCKED_UNSUPPORTED_FAMILY",
    "BLOCKED_MISSING_SOURCE",
    "BLOCKED_BACKTEST_PACK",
    "BLOCKED_ECONOMIC_GATE",
    "BLOCKED_MULTIPLICITY_ACCOUNT",
]


class ProfitCoreArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    path: str
    sha256: str
    artifact_id: str | None = None


class StrategyIdeaCandidateAuthoringBridgeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    family: str
    status: BridgeStatus
    symbols: list[str]
    blockers: list[str] = Field(default_factory=list)
    source_statuses: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    backtest_kill_gate_state: str | None = None
    profit_core_blocker_codes: list[str] = Field(default_factory=list)


class StrategyIdeaCandidateAuthoringBridgeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_authoring_bridge.v1"] = (
        AUTHORING_BRIDGE_SCHEMA_VERSION
    )
    manifest_id: str
    created_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    candidate_set_path: str
    candidate_set_sha256: str
    export_manifest_path: str
    export_manifest_sha256: str
    ledger_path: str
    ledger_sha256: str
    protocol_manifest_ref: ProfitCoreArtifactRef | None = None
    multiplicity_account_ref: ProfitCoreArtifactRef | None = None
    prep_watchdeck_root: str
    candidates: list[StrategyIdeaCandidateAuthoringBridgeCandidate]
    summary: dict[str, Any]
    known_gaps: list[str]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class StrategyIdeaCandidateAuthoringBridgeResult:
    manifest: StrategyIdeaCandidateAuthoringBridgeManifest
    manifest_path: Path
    manifest_sha256: str


class StrategyIdeaCandidateAuthoringBridgeOutputExistsError(ValueError):
    pass
