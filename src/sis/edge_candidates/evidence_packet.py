from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import PROFIT_CORE_EVIDENCE_PACKET_SCHEMA_VERSION
from sis.edge_candidates.backtest_kill_gate import BacktestKillGateDecision
from sis.edge_candidates.multiplicity import TrialMultiplicityAccount
from sis.edge_candidates.protocol import CandidateProtocolManifest
from sis.edge_candidates.virtual_execution_gate import VirtualExecutionGateDecision
from sis.strategy_idea_candidates.authoring_bridge import (
    StrategyIdeaCandidateAuthoringBridgeManifest,
)
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


SUPPORTED_CLAIM_TYPES = {
    "virtual_execution_verified",
    "after_cost_edge_over_no_trade",
    "no_trade_comparison_present",
}


class ClaimFindingSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKER = "BLOCKER"


class ClaimFindingCode(StrEnum):
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    MISSING_COMPARISON = "MISSING_COMPARISON"
    EVIDENCE_BASIS_MISMATCH = "EVIDENCE_BASIS_MISMATCH"
    ACTUAL_CASH_OVERCLAIM = "ACTUAL_CASH_OVERCLAIM"


class ProfitCoreArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_role: str
    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("artifact_role", "path")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact ref text fields must not be empty")
        return stripped


class ProfitCoreClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    claim_type: str
    claimed: bool
    requested_evidence_basis: str
    comparison_ref: str | None = None
    text: str

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("claim_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("claim_type", "requested_evidence_basis", "text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("claim text fields must not be empty")
        return stripped

    @field_validator("comparison_ref")
    @classmethod
    def validate_comparison_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProfitCoreClaimFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    finding_code: ClaimFindingCode
    severity: ClaimFindingSeverity
    message: str

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("claim_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped


class ProfitCoreEvidencePacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_evidence_packet.v1"] = (
        PROFIT_CORE_EVIDENCE_PACKET_SCHEMA_VERSION
    )
    packet_id: str
    generated_at: datetime
    producer: ProducerInfo
    candidate_id: str
    source_refs: list[ProfitCoreArtifactRef] = Field(min_length=1)
    claims: list[ProfitCoreClaim] = Field(default_factory=list)
    claim_findings: list[ProfitCoreClaimFinding] = Field(default_factory=list)
    machine_summary: dict[str, Any]
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "actual_cash": False,
            "permits_live_order": False,
            "permits_paper_order": False,
            "permits_actual_cash": False,
            "production_exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "llm_api_used": False,
        }
    )

    @field_validator("packet_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("generated_at", mode="before")
    @classmethod
    def validate_generated_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("generated_at", value)

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class ProfitCoreEvidencePacketWriteResult:
    packet: ProfitCoreEvidencePacket
    packet_path: Path
    packet_sha256: str


class ProfitCoreEvidencePacketError(ValueError):
    pass


class ProfitCoreEvidencePacketOutputExistsError(ProfitCoreEvidencePacketError):
    pass


def read_claims(path: Path | None) -> list[ProfitCoreClaim]:
    if path is None:
        return []
    payload = read_mapping_file(path)
    raw_claims = payload.get("claims", [])
    if not isinstance(raw_claims, list):
        raise ProfitCoreEvidencePacketError("claims file must contain a claims list")
    return [ProfitCoreClaim.model_validate(item) for item in raw_claims]


def build_profit_core_evidence_packet(
    *,
    protocol_path: Path,
    candidate_set_path: Path,
    bridge_manifest_path: Path,
    multiplicity_account_path: Path,
    backtest_kill_gate_path: Path,
    virtual_gate_path: Path,
    claims: list[ProfitCoreClaim],
    risk_review_source_paths: list[Path],
    candidate_id: str,
    generated_at: datetime | str | None = None,
) -> ProfitCoreEvidencePacket:
    protocol = CandidateProtocolManifest.model_validate(read_mapping_file(protocol_path))
    candidate_set = StrategyIdeaCandidateSet.model_validate(read_mapping_file(candidate_set_path))
    bridge = StrategyIdeaCandidateAuthoringBridgeManifest.model_validate(
        read_mapping_file(bridge_manifest_path)
    )
    multiplicity = TrialMultiplicityAccount.model_validate(
        read_mapping_file(multiplicity_account_path)
    )
    backtest_gate = BacktestKillGateDecision.model_validate(
        read_mapping_file(backtest_kill_gate_path)
    )
    virtual_gate = VirtualExecutionGateDecision.model_validate(read_mapping_file(virtual_gate_path))
    candidate = _candidate_payload(candidate_set, candidate_id)
    bridge_candidate = _bridge_candidate_payload(bridge, candidate_id)
    source_refs = [
        _artifact_ref("protocol", protocol_path, protocol.schema_version),
        _artifact_ref("candidate_set", candidate_set_path, candidate_set.schema_version),
        _artifact_ref("bridge_manifest", bridge_manifest_path, bridge.schema_version),
        _artifact_ref(
            "multiplicity_account",
            multiplicity_account_path,
            multiplicity.schema_version,
        ),
        _artifact_ref(
            "backtest_kill_gate",
            backtest_kill_gate_path,
            backtest_gate.schema_version,
        ),
        _artifact_ref("virtual_gate", virtual_gate_path, virtual_gate.schema_version),
    ]
    source_refs.extend(
        _artifact_ref("risk_review_source", path, _schema_version_for_path(path))
        for path in risk_review_source_paths
    )
    machine_summary = _machine_summary(
        protocol=protocol,
        candidate_set=candidate_set,
        candidate=candidate,
        bridge_candidate=bridge_candidate,
        multiplicity=multiplicity,
        backtest_gate=backtest_gate,
        virtual_gate=virtual_gate,
        claim_count=len(claims),
    )
    findings = diff_claims_against_machine_summary(claims, machine_summary)
    timestamp = _coerce_datetime(generated_at)
    return ProfitCoreEvidencePacket(
        packet_id=f"{candidate_id}-profit-core-evidence-packet",
        generated_at=timestamp,
        producer=ProducerInfo(command="edge-candidate-evidence-packet-build"),
        candidate_id=candidate_id,
        source_refs=source_refs,
        claims=claims,
        claim_findings=findings,
        machine_summary={**machine_summary, "finding_count": len(findings)},
    )


def build_and_write_profit_core_evidence_packet(
    *,
    protocol_path: Path,
    candidate_set_path: Path,
    bridge_manifest_path: Path,
    multiplicity_account_path: Path,
    backtest_kill_gate_path: Path,
    virtual_gate_path: Path,
    claims_path: Path | None,
    risk_review_source_paths: list[Path],
    candidate_id: str,
    out_dir: Path,
    generated_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> ProfitCoreEvidencePacketWriteResult:
    packet_path = out_dir / "profit_core_evidence_packet.json"
    if packet_path.exists() and not replace_existing:
        raise ProfitCoreEvidencePacketOutputExistsError(f"output already exists: {packet_path}")
    packet = build_profit_core_evidence_packet(
        protocol_path=protocol_path,
        candidate_set_path=candidate_set_path,
        bridge_manifest_path=bridge_manifest_path,
        multiplicity_account_path=multiplicity_account_path,
        backtest_kill_gate_path=backtest_kill_gate_path,
        virtual_gate_path=virtual_gate_path,
        claims=read_claims(claims_path),
        risk_review_source_paths=risk_review_source_paths,
        candidate_id=candidate_id,
        generated_at=generated_at,
    )
    write_json_artifact(packet_path, packet.model_dump(mode="json"))
    return ProfitCoreEvidencePacketWriteResult(
        packet=packet,
        packet_path=packet_path,
        packet_sha256=sha256_file(packet_path),
    )


def diff_claims_against_machine_summary(
    claims: list[ProfitCoreClaim],
    machine_summary: dict[str, Any],
) -> list[ProfitCoreClaimFinding]:
    findings: list[ProfitCoreClaimFinding] = []
    available_bases = set(machine_summary.get("evidence_bases", []))
    actual_cash_available = machine_summary.get("actual_cash_available") is True
    no_trade_present = machine_summary.get("no_trade_comparison_present") is True
    for claim in claims:
        if not claim.claimed:
            continue
        if (
            claim.claim_type not in SUPPORTED_CLAIM_TYPES
            and claim.claim_type != "actual_cash_result"
        ):
            findings.append(
                _finding(
                    claim,
                    ClaimFindingCode.UNSUPPORTED_CLAIM,
                    ClaimFindingSeverity.ERROR,
                    f"Unsupported claim_type: {claim.claim_type}",
                )
            )
        if claim.claim_type == "after_cost_edge_over_no_trade" and (
            claim.comparison_ref != "NO_TRADE" or not no_trade_present
        ):
            findings.append(
                _finding(
                    claim,
                    ClaimFindingCode.MISSING_COMPARISON,
                    ClaimFindingSeverity.WARNING,
                    "after_cost_edge_over_no_trade claims require NO_TRADE comparison evidence",
                )
            )
        if claim.claim_type == "actual_cash_result" and not actual_cash_available:
            findings.append(
                _finding(
                    claim,
                    ClaimFindingCode.ACTUAL_CASH_OVERCLAIM,
                    ClaimFindingSeverity.BLOCKER,
                    "actual_cash_result is claimed but no actual-cash evidence is available",
                )
            )
        elif claim.requested_evidence_basis not in available_bases:
            findings.append(
                _finding(
                    claim,
                    ClaimFindingCode.EVIDENCE_BASIS_MISMATCH,
                    ClaimFindingSeverity.ERROR,
                    (
                        "requested_evidence_basis is not available in machine evidence: "
                        f"{claim.requested_evidence_basis}"
                    ),
                )
            )
    return findings


def _machine_summary(
    *,
    protocol: CandidateProtocolManifest,
    candidate_set: StrategyIdeaCandidateSet,
    candidate: dict[str, Any],
    bridge_candidate: dict[str, Any],
    multiplicity: TrialMultiplicityAccount,
    backtest_gate: BacktestKillGateDecision,
    virtual_gate: VirtualExecutionGateDecision,
    claim_count: int,
) -> dict[str, Any]:
    evidence_bases = ["backtest", virtual_gate.evidence_basis]
    return {
        "protocol_id": protocol.protocol_id,
        "mode": protocol.mode.value,
        "candidate_set_id": candidate_set.candidate_set_id,
        "candidate_id": candidate["idea_candidate_id"],
        "candidate_decision": candidate["decision"],
        "bridge_status": bridge_candidate.get("status"),
        "multiplicity_success_only_reporting": multiplicity.success_only_reporting,
        "multiplicity_sealed_test_used_for_selection": (
            multiplicity.sealed_test_used_for_selection
        ),
        "backtest_gate_state": backtest_gate.gate_state.value,
        "no_trade_comparison_present": backtest_gate.summary.get("no_trade_comparison_present")
        is True,
        "virtual_gate_state": virtual_gate.gate_state.value,
        "cash_metric_basis": virtual_gate.cash_metric_basis,
        "evidence_bases": list(dict.fromkeys(evidence_bases)),
        "actual_cash_available": False,
        "actual_cash": False,
        "permits_live_order": False,
        "production_exchange_write_used": False,
        "live_order_submitted": False,
        "profit_evidence": False,
        "claim_count": claim_count,
    }


def _candidate_payload(
    candidate_set: StrategyIdeaCandidateSet, candidate_id: str
) -> dict[str, Any]:
    for candidate in candidate_set.candidate_inventory:
        if candidate.idea_candidate_id == candidate_id:
            return candidate.model_dump(mode="json")
    raise ProfitCoreEvidencePacketError(f"candidate not found: {candidate_id}")


def _bridge_candidate_payload(
    bridge: StrategyIdeaCandidateAuthoringBridgeManifest,
    candidate_id: str,
) -> dict[str, Any]:
    for candidate in bridge.candidates:
        if candidate.candidate_id == candidate_id:
            return candidate.model_dump(mode="json")
    raise ProfitCoreEvidencePacketError(f"bridge candidate not found: {candidate_id}")


def _artifact_ref(role: str, path: Path, schema_version: str | None) -> ProfitCoreArtifactRef:
    return ProfitCoreArtifactRef(
        artifact_role=role,
        path=path.as_posix(),
        sha256=sha256_file(path),
        schema_version=schema_version,
    )


def _schema_version_for_path(path: Path) -> str | None:
    try:
        payload = read_mapping_file(path)
    except Exception:
        return None
    value = payload.get("schema_version")
    return str(value) if value is not None else None


def _finding(
    claim: ProfitCoreClaim,
    code: ClaimFindingCode,
    severity: ClaimFindingSeverity,
    message: str,
) -> ProfitCoreClaimFinding:
    return ProfitCoreClaimFinding(
        claim_id=claim.claim_id,
        finding_code=code,
        severity=severity,
        message=message,
    )


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return ensure_utc_aware("generated_at", value)


__all__ = [
    "ClaimFindingCode",
    "ClaimFindingSeverity",
    "ProfitCoreArtifactRef",
    "ProfitCoreClaim",
    "ProfitCoreClaimFinding",
    "ProfitCoreEvidencePacket",
    "ProfitCoreEvidencePacketError",
    "ProfitCoreEvidencePacketOutputExistsError",
    "ProfitCoreEvidencePacketWriteResult",
    "build_and_write_profit_core_evidence_packet",
    "build_profit_core_evidence_packet",
    "diff_claims_against_machine_summary",
    "read_claims",
]
