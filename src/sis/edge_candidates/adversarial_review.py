from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import PROFIT_CORE_ADVERSARIAL_REVIEW_SCHEMA_VERSION
from sis.edge_candidates.evidence_packet import (
    ClaimFindingCode,
    ClaimFindingSeverity,
    ProfitCoreClaimFinding,
    ProfitCoreEvidencePacket,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


class ProfitCoreAdversarialReviewStatus(StrEnum):
    ADVERSARIAL_FINDING = "ADVERSARIAL_FINDING"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    OVERCLAIM_FLAG = "OVERCLAIM_FLAG"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    NO_ADDITIONAL_BLOCKER_FOUND = "NO_ADDITIONAL_BLOCKER_FOUND"


class ProfitCoreAdversarialFindingSource(StrEnum):
    MACHINE_CLAIM_DIFF = "MACHINE_CLAIM_DIFF"
    MANUAL_ADVERSARIAL_REVIEW = "MANUAL_ADVERSARIAL_REVIEW"


class ProfitCoreAdversarialEvidenceRefType(StrEnum):
    EVIDENCE_PACKET = "evidence_packet"
    CLAIM_FINDING = "claim_finding"
    CLAIM = "claim"
    MACHINE_SUMMARY = "machine_summary"


class ProfitCoreAdversarialEvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ref_type: ProfitCoreAdversarialEvidenceRefType
    ref_id: str | None = None
    path: str | None = None
    sha256: str | None = None

    @field_validator("ref_id")
    @classmethod
    def validate_ref_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("ref_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("path", "sha256")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProfitCoreAdversarialFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str
    status: ProfitCoreAdversarialReviewStatus
    severity: ClaimFindingSeverity
    message: str
    source: ProfitCoreAdversarialFindingSource
    evidence_refs: list[ProfitCoreAdversarialEvidenceRef] = Field(default_factory=list)
    machine_checkable: bool = False
    hard_blocker: bool = False

    @field_validator("finding_id")
    @classmethod
    def validate_finding_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("finding_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped

    @field_validator("hard_blocker")
    @classmethod
    def validate_hard_blocker(cls, value: bool, info) -> bool:
        machine_checkable = info.data.get("machine_checkable") is True
        if value and not machine_checkable:
            raise ValueError("hard_blocker requires machine_checkable=true")
        return value


class ProfitCoreAdversarialReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_adversarial_review.v1"] = (
        PROFIT_CORE_ADVERSARIAL_REVIEW_SCHEMA_VERSION
    )
    review_id: str
    recorded_at: datetime
    producer: ProducerInfo
    candidate_id: str
    evidence_packet_ref: ProfitCoreAdversarialEvidenceRef
    review_status: ProfitCoreAdversarialReviewStatus
    findings: list[ProfitCoreAdversarialFinding] = Field(default_factory=list)
    machine_finding_count: int = Field(ge=0)
    manual_finding_count: int = Field(ge=0)
    hard_blocker_count: int = Field(ge=0)
    review_mode: Literal["local_manual_import"] = "local_manual_import"
    redaction_policy: Literal["LOCAL_ONLY_NO_EXTERNAL_SEND"] = "LOCAL_ONLY_NO_EXTERNAL_SEND"
    llm_api_used: Literal[False] = False
    external_send_performed: Literal[False] = False
    approval_allowed: Literal[False] = False
    permission_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    tiny_live_allowed: Literal[False] = False
    no_additional_blocker_is_approval: Literal[False] = False
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "actual_cash_decision_allowed": False,
            "permits_live_order": False,
            "permits_paper_order": False,
            "permits_tiny_live": False,
            "permits_actual_cash": False,
            "production_exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "llm_api_used": False,
            "external_send_performed": False,
            "gate_override_allowed": False,
            "strategy_rewrite_allowed": False,
            "pnl_metric_authority": False,
        }
    )

    @field_validator("review_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("recorded_at", mode="before")
    @classmethod
    def validate_recorded_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("recorded_at", value)

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class ProfitCoreAdversarialReviewWriteResult:
    review: ProfitCoreAdversarialReview
    review_path: Path
    review_sha256: str


class ProfitCoreAdversarialReviewError(ValueError):
    pass


class ProfitCoreAdversarialReviewOutputExistsError(ProfitCoreAdversarialReviewError):
    pass


def build_profit_core_adversarial_review(
    *,
    evidence_packet_path: Path,
    manual_review_path: Path | None,
    recorded_at: datetime | str | None = None,
) -> ProfitCoreAdversarialReview:
    evidence_packet = ProfitCoreEvidencePacket.model_validate(
        read_mapping_file(evidence_packet_path)
    )
    machine_findings = [
        _finding_from_claim_finding(finding) for finding in evidence_packet.claim_findings
    ]
    manual_findings = read_manual_adversarial_findings(manual_review_path)
    findings = [*machine_findings, *manual_findings]
    hard_blocker_count = sum(1 for finding in findings if finding.hard_blocker)
    timestamp = _coerce_datetime(recorded_at)
    return ProfitCoreAdversarialReview(
        review_id=f"{evidence_packet.candidate_id}-profit-core-adversarial-review",
        recorded_at=timestamp,
        producer=ProducerInfo(command="edge-candidate-adversarial-review-record"),
        candidate_id=evidence_packet.candidate_id,
        evidence_packet_ref=ProfitCoreAdversarialEvidenceRef(
            ref_type=ProfitCoreAdversarialEvidenceRefType.EVIDENCE_PACKET,
            ref_id=evidence_packet.packet_id,
            path=evidence_packet_path.as_posix(),
            sha256=sha256_file(evidence_packet_path),
        ),
        review_status=_derive_review_status(findings),
        findings=findings,
        machine_finding_count=len(machine_findings),
        manual_finding_count=len(manual_findings),
        hard_blocker_count=hard_blocker_count,
    )


def build_and_write_profit_core_adversarial_review(
    *,
    evidence_packet_path: Path,
    manual_review_path: Path | None,
    out_dir: Path,
    recorded_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> ProfitCoreAdversarialReviewWriteResult:
    review_path = out_dir / "profit_core_adversarial_review.json"
    if review_path.exists() and not replace_existing:
        raise ProfitCoreAdversarialReviewOutputExistsError(f"output already exists: {review_path}")
    review = build_profit_core_adversarial_review(
        evidence_packet_path=evidence_packet_path,
        manual_review_path=manual_review_path,
        recorded_at=recorded_at,
    )
    write_json_artifact(review_path, review.model_dump(mode="json"))
    return ProfitCoreAdversarialReviewWriteResult(
        review=review,
        review_path=review_path,
        review_sha256=sha256_file(review_path),
    )


def read_manual_adversarial_findings(path: Path | None) -> list[ProfitCoreAdversarialFinding]:
    if path is None:
        return []
    payload = read_mapping_file(path)
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        raise ProfitCoreAdversarialReviewError("manual review file must contain a findings list")
    findings: list[ProfitCoreAdversarialFinding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            raise ProfitCoreAdversarialReviewError("manual findings must be objects")
        if raw.get("hard_blocker") is True:
            raise ProfitCoreAdversarialReviewError("manual findings cannot set hard_blocker")
        finding_payload = {
            **raw,
            "source": ProfitCoreAdversarialFindingSource.MANUAL_ADVERSARIAL_REVIEW,
            "machine_checkable": False,
            "hard_blocker": False,
        }
        findings.append(ProfitCoreAdversarialFinding.model_validate(finding_payload))
    return findings


def _finding_from_claim_finding(
    finding: ProfitCoreClaimFinding,
) -> ProfitCoreAdversarialFinding:
    status = _status_for_claim_finding(finding.finding_code)
    hard_blocker = finding.severity is ClaimFindingSeverity.BLOCKER
    return ProfitCoreAdversarialFinding(
        finding_id=f"machine-{finding.finding_code.value.lower()}-{finding.claim_id}",
        status=status,
        severity=finding.severity,
        message=finding.message,
        source=ProfitCoreAdversarialFindingSource.MACHINE_CLAIM_DIFF,
        evidence_refs=[
            ProfitCoreAdversarialEvidenceRef(
                ref_type=ProfitCoreAdversarialEvidenceRefType.CLAIM_FINDING,
                ref_id=finding.claim_id,
            )
        ],
        machine_checkable=True,
        hard_blocker=hard_blocker,
    )


def _status_for_claim_finding(
    code: ClaimFindingCode,
) -> ProfitCoreAdversarialReviewStatus:
    if code is ClaimFindingCode.MISSING_COMPARISON:
        return ProfitCoreAdversarialReviewStatus.NEEDS_MORE_EVIDENCE
    if code in {
        ClaimFindingCode.EVIDENCE_BASIS_MISMATCH,
        ClaimFindingCode.ACTUAL_CASH_OVERCLAIM,
    }:
        return ProfitCoreAdversarialReviewStatus.OVERCLAIM_FLAG
    return ProfitCoreAdversarialReviewStatus.ADVERSARIAL_FINDING


def _derive_review_status(
    findings: list[ProfitCoreAdversarialFinding],
) -> ProfitCoreAdversarialReviewStatus:
    statuses = {finding.status for finding in findings}
    for status in (
        ProfitCoreAdversarialReviewStatus.OVERCLAIM_FLAG,
        ProfitCoreAdversarialReviewStatus.NEEDS_MORE_EVIDENCE,
        ProfitCoreAdversarialReviewStatus.HUMAN_REVIEW_REQUIRED,
        ProfitCoreAdversarialReviewStatus.ADVERSARIAL_FINDING,
    ):
        if status in statuses:
            return status
    return ProfitCoreAdversarialReviewStatus.NO_ADDITIONAL_BLOCKER_FOUND


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return ensure_utc_aware("recorded_at", value)


__all__ = [
    "ProfitCoreAdversarialEvidenceRef",
    "ProfitCoreAdversarialEvidenceRefType",
    "ProfitCoreAdversarialFinding",
    "ProfitCoreAdversarialFindingSource",
    "ProfitCoreAdversarialReview",
    "ProfitCoreAdversarialReviewError",
    "ProfitCoreAdversarialReviewOutputExistsError",
    "ProfitCoreAdversarialReviewStatus",
    "ProfitCoreAdversarialReviewWriteResult",
    "build_and_write_profit_core_adversarial_review",
    "build_profit_core_adversarial_review",
    "read_manual_adversarial_findings",
]
