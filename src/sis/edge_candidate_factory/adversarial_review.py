from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sis.backtest.artifact_io import sha256_file
from sis.edge_candidate_factory._contracts import (
    LLMAdversarialReviewStatus,
    LLMFindingSeverity,
    LLMFindingType,
)
from sis.edge_candidate_factory.generator import ZERO_HASH
from sis.edge_candidate_factory.models import (
    ArtifactRef,
    LLMAdversarialEvidenceReview,
    LLMAdversarialFinding,
    ProducerInfo,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_review.provenance import repo_relative_path


ADVERSARIAL_PACKET_SCHEMA_VERSION = "edge_candidate_adversarial_packet.v1"


@dataclass(frozen=True)
class AdversarialPacketResult:
    packet: dict[str, Any]
    packet_path: Path


@dataclass(frozen=True)
class AdversarialReviewImportResult:
    review: LLMAdversarialEvidenceReview
    review_path: Path


def _schema_version(path: Path) -> str:
    if not path.exists() or path.suffix.lower() != ".json":
        return "unknown.v1"
    try:
        payload = read_mapping_file(path)
    except Exception:
        return "unknown.v1"
    value = payload.get("schema_version")
    return str(value) if isinstance(value, str) and value else "unknown.v1"


def _display_path(path: Path) -> str:
    try:
        return repo_relative_path(path)
    except ValueError:
        return f"external/{path.name}"


def _packet_source(path: Path, index: int) -> dict[str, Any]:
    exists = path.exists()
    return {
        "ref_id": f"source-{index:03d}",
        "schema_version": _schema_version(path),
        "path": _display_path(path),
        "sha256": sha256_file(path) if exists else ZERO_HASH,
        "exists": exists,
    }


def build_adversarial_packet(
    *,
    packet_id: str,
    created_at: datetime,
    source_paths: list[Path],
    out_dir: Path,
) -> AdversarialPacketResult:
    sources = [_packet_source(path, index) for index, path in enumerate(source_paths, start=1)]
    packet = {
        "schema_version": ADVERSARIAL_PACKET_SCHEMA_VERSION,
        "packet_id": packet_id,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "producer": {"tool": "sis", "command": "edge-candidate-adversarial-packet-build"},
        "network_attempted": False,
        "credentials_used": False,
        "llm_api_called": False,
        "sources": sources,
        "review_instructions": [
            "Find missing artifacts, contradictions, overclaims, and actual-cash confusion.",
            "Do not approve paper, live, actual cash, or gate override decisions.",
        ],
    }
    packet_path = out_dir / "adversarial_packet.json"
    write_json_artifact(packet_path, packet)
    return AdversarialPacketResult(packet=packet, packet_path=packet_path)


def _packet_sources(packet: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sources = packet.get("sources", [])
    return [source for source in raw_sources if isinstance(source, dict)]


def _source_ref(source: dict[str, Any]) -> ArtifactRef:
    return ArtifactRef(
        ref_id=str(source.get("ref_id") or "source"),
        schema_version=str(source.get("schema_version") or "unknown.v1"),
        path=str(source.get("path") or "unknown"),
        sha256=str(source.get("sha256") or ZERO_HASH),
    )


def _missing_source_findings(packet: dict[str, Any]) -> list[LLMAdversarialFinding]:
    findings = []
    for index, source in enumerate(_packet_sources(packet), start=1):
        if source.get("exists") is not False:
            continue
        path = str(source.get("path") or "unknown")
        findings.append(
            LLMAdversarialFinding(
                finding_id=f"missing-artifact-{index:03d}",
                finding_type=LLMFindingType.MISSING_ARTIFACT,
                severity=LLMFindingSeverity.HARD,
                source_ref=path,
                claim_text="source artifact is required for adversarial evidence review",
                problem="source artifact is missing",
                required_fix="provide the missing source artifact before relying on this review",
                machine_checkable=True,
                hard_blocker=True,
            )
        )
    return findings


def _finding_type(value: object) -> LLMFindingType:
    if isinstance(value, str):
        for finding_type in LLMFindingType:
            if value == finding_type.value:
                return finding_type
    return LLMFindingType.OVERCLAIM_FLAG


def _manual_findings(response: dict[str, Any]) -> list[LLMAdversarialFinding]:
    raw_findings = response.get("findings", [])
    findings: list[LLMAdversarialFinding] = []
    if not isinstance(raw_findings, list):
        return findings
    for index, raw in enumerate(raw_findings, start=1):
        if not isinstance(raw, dict):
            continue
        item = cast(dict[str, Any], raw)
        machine_checkable = bool(item.get("machine_checkable"))
        hard_blocker = bool(item.get("hard_blocker")) and machine_checkable
        findings.append(
            LLMAdversarialFinding(
                finding_id=str(item.get("finding_id") or f"manual-finding-{index:03d}"),
                finding_type=_finding_type(item.get("finding_type")),
                severity=LLMFindingSeverity.HARD if hard_blocker else LLMFindingSeverity.SOFT,
                source_ref=str(item.get("source_ref") or "manual_response"),
                claim_text=str(item.get("claim_text") or "manual adversarial claim"),
                problem=str(item.get("problem") or "manual adversarial finding"),
                required_fix=str(item.get("required_fix") or "human review required"),
                machine_checkable=machine_checkable,
                hard_blocker=hard_blocker,
            )
        )
    return findings


def _review_status(
    *,
    findings: list[LLMAdversarialFinding],
    response: dict[str, Any],
) -> LLMAdversarialReviewStatus:
    if any(finding.finding_type is LLMFindingType.MISSING_ARTIFACT for finding in findings):
        return LLMAdversarialReviewStatus.MISSING_ARTIFACT
    if any(finding.hard_blocker for finding in findings):
        return LLMAdversarialReviewStatus.HUMAN_REVIEW_REQUIRED
    if findings:
        raw_status = response.get("review_status")
        if isinstance(raw_status, str):
            for status in LLMAdversarialReviewStatus:
                if raw_status == status.value:
                    return status
        return LLMAdversarialReviewStatus.ADVERSARIAL_FINDING
    return LLMAdversarialReviewStatus.NO_BLOCKING_FINDING


def import_adversarial_review(
    *,
    review_id: str,
    created_at: datetime,
    packet_path: Path,
    response_path: Path,
    out_dir: Path,
) -> AdversarialReviewImportResult:
    packet = read_mapping_file(packet_path)
    response = read_mapping_file(response_path)
    findings = [*_missing_source_findings(packet), *_manual_findings(response)]
    hard_blocker_count = sum(1 for finding in findings if finding.hard_blocker)
    soft_warning_count = len(findings) - hard_blocker_count
    review = LLMAdversarialEvidenceReview(
        review_id=review_id,
        created_at=created_at,
        producer=ProducerInfo(command="edge-candidate-adversarial-import"),
        source_refs=[_source_ref(source) for source in _packet_sources(packet)],
        packet_hash=sha256_file(packet_path),
        review_status=_review_status(findings=findings, response=response),
        findings=findings,
        hard_blocker_count=hard_blocker_count,
        soft_warning_count=soft_warning_count,
        llm_approval_ignored=True,
        paper_execution_allowed=False,
        live_allowed=False,
        actual_cash_decision_allowed=False,
        gate_override_allowed=False,
    )
    review_path = out_dir / "llm_adversarial_review.json"
    write_json_artifact(review_path, review.model_dump(mode="json"))
    return AdversarialReviewImportResult(review=review, review_path=review_path)
