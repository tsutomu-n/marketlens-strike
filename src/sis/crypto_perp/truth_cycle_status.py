from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


TRUTH_CYCLE_STATUS_SCHEMA_VERSION = "crypto_perp_truth_cycle_status.v1"

TruthCycleStatus = Literal[
    "MISSING_PROBE_AUDIT",
    "BLOCKED_PROBE_QUALITY",
    "READY_FOR_RAW_REFRESH",
    "RAW_REFRESH_NO_EVENT",
    "READY_FOR_DECISION",
    "READY_FOR_OUTCOME_AFTER_MATURITY",
    "READY_FOR_ROWS_PREVIEW",
    "READY_FOR_TOURNAMENT_REPORT",
    "READY_FOR_TOURNAMENT_GATE",
    "READY_FOR_HUMAN_TINY_LIVE_REVIEW",
    "NEEDS_MORE_EVIDENCE",
    "NEEDS_ACTUAL_CASH",
    "HOLD_NO_TRADE_LEADS",
    "REVISE_OR_RETIRE",
]


class TruthCycleStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str
    artifact_path: str | None = None
    present: bool
    schema_version: str | None = None
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class CryptoPerpTruthCycleStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_truth_cycle_status.v1"] = (
        TRUTH_CYCLE_STATUS_SCHEMA_VERSION
    )
    artifact_id: str
    producer: CryptoPerpProducer
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    cycle_status: TruthCycleStatus
    recommended_next_command: str
    stop_reasons: list[str]
    stages: list[TruthCycleStage]
    known_gaps: list[str]
    summary: dict[str, Any]


def _load_json(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None or not path.exists():
        return None, None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact must be a JSON object: {path}")
    return payload, str(payload.get("schema_version") or "")


def _stage(stage_id: str, path: Path | None, payload: dict[str, Any] | None) -> TruthCycleStage:
    return TruthCycleStage(
        stage_id=stage_id,
        artifact_path=path.as_posix() if path is not None else None,
        present=payload is not None,
        schema_version=str(payload.get("schema_version")) if payload is not None else None,
        status=_stage_status(stage_id, payload),
        details=_stage_details(stage_id, payload),
    )


def _stage_status(stage_id: str, payload: dict[str, Any] | None) -> str:
    if payload is None:
        return "missing"
    if stage_id == "probe_audit":
        return str(payload.get("audit_status", "present"))
    if stage_id == "raw_refresh":
        event_count = int(payload.get("event_count") or 0)
        return "EVENTS_PRESENT" if event_count > 0 else "NO_EVENT_DETECTED"
    if stage_id == "tournament_report":
        return str(payload.get("tournament_status", "present"))
    if stage_id == "tournament_gate":
        return str(payload.get("gate_status", "present"))
    return "present"


def _stage_details(stage_id: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {}
    if stage_id == "probe_audit":
        return {
            "known_gap_count": len(payload.get("known_gaps") or []),
            "network_attempted": payload.get("summary", {}).get("network_attempted"),
            "credentials_used": payload.get("summary", {}).get("credentials_used"),
        }
    if stage_id == "raw_refresh":
        return {
            "event_count": payload.get("event_count"),
            "known_gap_count": len(payload.get("known_gaps") or []),
        }
    if stage_id == "tournament_report":
        return {
            "leader_action": payload.get("leader_action"),
            "event_count": payload.get("event_count"),
            "known_gap_count": len(payload.get("known_gaps") or []),
        }
    if stage_id == "tournament_gate":
        return {
            "recommended_action": payload.get("recommended_action"),
            "failed_condition_count": len(payload.get("failed_conditions") or []),
            "known_gap_count": len(payload.get("known_gaps") or []),
        }
    return {}


def _known_gaps(*payloads: dict[str, Any] | None) -> list[str]:
    gaps: list[str] = []
    for payload in payloads:
        if payload is None:
            continue
        for gap in payload.get("known_gaps") or []:
            gaps.append(str(gap))
    return list(dict.fromkeys(gaps))


def _status_and_next(
    *,
    probe_audit: dict[str, Any] | None,
    raw_refresh: dict[str, Any] | None,
    event: dict[str, Any] | None,
    decision: dict[str, Any] | None,
    outcome: dict[str, Any] | None,
    rows_preview: dict[str, Any] | None,
    tournament_report: dict[str, Any] | None,
    tournament_gate: dict[str, Any] | None,
) -> tuple[TruthCycleStatus, str, list[str]]:
    if tournament_gate is not None:
        gate_status = str(tournament_gate.get("gate_status"))
        if gate_status in {
            "READY_FOR_HUMAN_TINY_LIVE_REVIEW",
            "NEEDS_MORE_EVIDENCE",
            "NEEDS_ACTUAL_CASH",
            "HOLD_NO_TRADE_LEADS",
            "REVISE_OR_RETIRE",
        }:
            return gate_status, str(tournament_gate.get("recommended_action") or ""), []
        return "REVISE_OR_RETIRE", "inspect_tournament_gate_artifact", ["UNKNOWN_GATE_STATUS"]

    if tournament_report is not None:
        return (
            "READY_FOR_TOURNAMENT_GATE",
            "uv run sis crypto-perp-tournament-gate --report <tournament_report.json> --out <gate-dir>",
            [],
        )
    if rows_preview is not None:
        return (
            "READY_FOR_TOURNAMENT_REPORT",
            "uv run sis crypto-perp-tournament-report --rows <tournament_rows_preview.json> --out <report-dir> --min-events 10",
            [],
        )
    if outcome is not None:
        return (
            "READY_FOR_ROWS_PREVIEW",
            "uv run sis crypto-perp-tournament-rows-preview --outcome <outcome.json> --out <rows-preview-dir>",
            [],
        )
    if decision is not None:
        return (
            "READY_FOR_OUTCOME_AFTER_MATURITY",
            "uv run sis crypto-perp-outcome-record --event <event.json> --out <outcome-dir> --horizon-minutes <minutes> --reference-price <price> --close-price <price> --high-price <price> --low-price <price>",
            ["WAIT_FOR_MATURITY_BEFORE_RECORDING_OUTCOME"],
        )
    if event is not None:
        return (
            "READY_FOR_DECISION",
            "uv run sis crypto-perp-decision-record --event <event.json> --action <REVERSAL_SHORT|CONTINUATION_LONG|NO_TRADE|UNKNOWN> --out <decision-dir>",
            ["DECISION_MUST_BE_RECORDED_BEFORE_OUTCOME"],
        )
    if raw_refresh is not None:
        event_count = int(raw_refresh.get("event_count") or 0)
        if event_count <= 0:
            return (
                "RAW_REFRESH_NO_EVENT",
                "inspect raw_refresh known_gaps, then rerun public probe later or revise event detector thresholds",
                ["NO_EVENT_DETECTED"],
            )
        return (
            "READY_FOR_DECISION",
            "select raw_refresh event_paths[0], then run crypto-perp-decision-record before outcome",
            ["EVENT_ARTIFACT_NOT_PASSED_TO_STATUS_COMMAND"],
        )
    if probe_audit is None:
        return (
            "MISSING_PROBE_AUDIT",
            "uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>",
            ["PROBE_AUDIT_REQUIRED_BEFORE_EVENT_REFRESH"],
        )
    if probe_audit.get("audit_status") != "READY_FOR_EVENT_REFRESH":
        return (
            "BLOCKED_PROBE_QUALITY",
            "repair_or_rerun_public_probe_before_event_refresh",
            [str(item) for item in probe_audit.get("known_gaps") or ["PROBE_AUDIT_NOT_READY"]],
        )
    return (
        "READY_FOR_RAW_REFRESH",
        "uv run sis crypto-perp-raw-refresh --probe <provider_probe.json> --probe-audit <probe_audit.json> --out <raw-refresh-dir>",
        [],
    )


def build_truth_cycle_status(
    *,
    probe_audit_path: Path | None = None,
    raw_refresh_path: Path | None = None,
    event_path: Path | None = None,
    decision_path: Path | None = None,
    outcome_path: Path | None = None,
    rows_preview_path: Path | None = None,
    tournament_report_path: Path | None = None,
    tournament_gate_path: Path | None = None,
    producer_command: str = "crypto-perp-truth-cycle-status",
) -> CryptoPerpTruthCycleStatus:
    probe_audit, _ = _load_json(probe_audit_path)
    raw_refresh, _ = _load_json(raw_refresh_path)
    event, _ = _load_json(event_path)
    decision, _ = _load_json(decision_path)
    outcome, _ = _load_json(outcome_path)
    rows_preview, _ = _load_json(rows_preview_path)
    tournament_report, _ = _load_json(tournament_report_path)
    tournament_gate, _ = _load_json(tournament_gate_path)
    cycle_status, next_command, stop_reasons = _status_and_next(
        probe_audit=probe_audit,
        raw_refresh=raw_refresh,
        event=event,
        decision=decision,
        outcome=outcome,
        rows_preview=rows_preview,
        tournament_report=tournament_report,
        tournament_gate=tournament_gate,
    )
    stages = [
        _stage("probe_audit", probe_audit_path, probe_audit),
        _stage("raw_refresh", raw_refresh_path, raw_refresh),
        _stage("event", event_path, event),
        _stage("decision", decision_path, decision),
        _stage("outcome", outcome_path, outcome),
        _stage("tournament_rows_preview", rows_preview_path, rows_preview),
        _stage("tournament_report", tournament_report_path, tournament_report),
        _stage("tournament_gate", tournament_gate_path, tournament_gate),
    ]
    known_gaps = _known_gaps(probe_audit, raw_refresh, rows_preview, tournament_report, tournament_gate)
    summary = {
        "cycle_status": cycle_status,
        "present_stage_count": sum(1 for stage in stages if stage.present),
        "known_gap_count": len(known_gaps),
        "stop_reason_count": len(stop_reasons),
    }
    return CryptoPerpTruthCycleStatus(
        artifact_id=stable_hash(["crypto-perp-truth-cycle-status", summary, known_gaps]),
        producer=CryptoPerpProducer(command=producer_command),
        cycle_status=cycle_status,
        recommended_next_command=next_command,
        stop_reasons=stop_reasons,
        stages=stages,
        known_gaps=known_gaps,
        summary=summary,
    )
