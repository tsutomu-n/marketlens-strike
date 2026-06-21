from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sis.crypto_perp.bitget.probe import ProviderProbeArtifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


REQUIRED_PUBLIC_ENDPOINTS = ("instruments", "tickers", "candles")


class CryptoPerpProbeAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_probe_audit.v1"] = "crypto_perp_probe_audit.v1"
    artifact_id: str
    producer: CryptoPerpProducer
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    probe_id: str
    audit_status: Literal["READY_FOR_EVENT_REFRESH", "BLOCKED_PROBE_QUALITY"]
    required_endpoints: list[str]
    present_endpoints: list[str]
    missing_endpoints: list[str]
    zero_row_endpoints: list[str]
    failed_endpoints: list[str]
    missing_capabilities: list[str]
    raw_snapshot_count: int
    missing_raw_snapshot_paths: list[str]
    next_actions: list[str]
    known_gaps: list[str]
    summary: dict[str, Any]


def build_probe_audit(
    *,
    probe: ProviderProbeArtifact,
    check_raw_exists: bool = True,
) -> CryptoPerpProbeAudit:
    endpoint_by_id = {item.endpoint_id: item for item in probe.endpoint_results}
    present = sorted(endpoint_by_id)
    missing = [endpoint for endpoint in REQUIRED_PUBLIC_ENDPOINTS if endpoint not in endpoint_by_id]
    zero_rows = [
        endpoint
        for endpoint in REQUIRED_PUBLIC_ENDPOINTS
        if endpoint in endpoint_by_id and endpoint_by_id[endpoint].row_count <= 0
    ]
    failed = sorted(
        item.endpoint_id
        for item in probe.endpoint_results
        if item.status_code < 200 or item.status_code >= 300 or item.error_class is not None
    )
    capabilities = probe.capabilities.model_dump(mode="json")
    missing_capabilities = [
        name
        for name in ["instruments", "tickers", "candle_15m"]
        if capabilities.get(name) is not True
    ]
    missing_raw_paths = (
        [ref.path for ref in probe.source_refs if not Path(ref.path).exists()]
        if check_raw_exists
        else []
    )
    known_gaps = list(
        dict.fromkeys(missing + zero_rows + failed + missing_capabilities + missing_raw_paths)
    )
    ready = not known_gaps and probe.network_attempted and not probe.credentials_used
    audit_status: Literal["READY_FOR_EVENT_REFRESH", "BLOCKED_PROBE_QUALITY"] = (
        "READY_FOR_EVENT_REFRESH" if ready else "BLOCKED_PROBE_QUALITY"
    )
    next_actions = (
        [
            "build_universe_snapshot_from_probe_raw",
            "build_market_snapshot_from_probe_raw",
            "detect_candidate_events",
        ]
        if ready
        else ["repair_or_rerun_public_probe_before_event_refresh"]
    )
    summary = {
        "probe_id": probe.probe_id,
        "audit_status": audit_status,
        "network_attempted": probe.network_attempted,
        "credentials_used": probe.credentials_used,
        "required_endpoint_count": len(REQUIRED_PUBLIC_ENDPOINTS),
        "raw_snapshot_count": len(probe.source_refs),
        "known_gap_count": len(known_gaps),
    }
    return CryptoPerpProbeAudit(
        artifact_id=stable_hash(["crypto-perp-probe-audit", probe.probe_id, summary]),
        producer=CryptoPerpProducer(command="crypto-perp-probe-audit"),
        probe_id=probe.probe_id,
        audit_status=audit_status,
        required_endpoints=list(REQUIRED_PUBLIC_ENDPOINTS),
        present_endpoints=present,
        missing_endpoints=missing,
        zero_row_endpoints=zero_rows,
        failed_endpoints=failed,
        missing_capabilities=missing_capabilities,
        raw_snapshot_count=len(probe.source_refs),
        missing_raw_snapshot_paths=missing_raw_paths,
        next_actions=next_actions,
        known_gaps=known_gaps,
        summary=summary,
    )
