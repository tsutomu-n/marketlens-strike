from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

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


class TruthCycleNextStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    purpose: str
    command: str
    requires_explicit_approval: bool = False
    network_allowed: Literal[False] = False
    exchange_write_allowed: Literal[False] = False
    live_order_allowed: Literal[False] = False


class TruthCycleStageChecklistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str
    status: str
    present: bool
    blocks_progress: bool
    artifact_path: str | None = None
    expected_cli_option: str | None = None
    expected_artifact_hint: str


class CryptoPerpTruthCycleStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_truth_cycle_status.v1"] = TRUTH_CYCLE_STATUS_SCHEMA_VERSION
    artifact_id: str
    producer: CryptoPerpProducer
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    cycle_status: TruthCycleStatus
    recommended_next_command: str
    next_steps: list[TruthCycleNextStep]
    stop_reasons: list[str]
    stages: list[TruthCycleStage]
    stage_checklist: list[TruthCycleStageChecklistItem]
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
        status=_stage_status(stage_id, path, payload),
        details=_stage_details(stage_id, path, payload),
    )


def _stage_status(stage_id: str, path: Path | None, payload: dict[str, Any] | None) -> str:
    if payload is None:
        if path is not None and not path.exists():
            return "path_not_found"
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


def _stage_details(
    stage_id: str, path: Path | None, payload: dict[str, Any] | None
) -> dict[str, Any]:
    if payload is None:
        if path is not None and not path.exists():
            return {"path_exists": False}
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


def _missing_path_stop_reasons(stages: list[TruthCycleStage]) -> list[str]:
    return [
        f"{stage.stage_id.upper()}_ARTIFACT_PATH_NOT_FOUND"
        for stage in stages
        if stage.artifact_path is not None and stage.status == "path_not_found"
    ]


def _gate_stop_reasons(gate: dict[str, Any], gate_status: str) -> list[str]:
    reasons = [f"GATE_STATUS_{gate_status}"]
    for condition in gate.get("failed_conditions") or []:
        if isinstance(condition, dict):
            condition_id = str(condition.get("condition_id") or "").strip()
            if condition_id:
                reasons.append(f"GATE_FAILED_CONDITION_{condition_id}")
    return list(dict.fromkeys(reasons))


def _human_summary(cycle_status: TruthCycleStatus, stop_reasons: list[str]) -> str:
    if cycle_status == "MISSING_PROBE_AUDIT":
        if any(reason.endswith("_ARTIFACT_PATH_NOT_FOUND") for reason in stop_reasons):
            return "指定された probe audit artifact が見つからないため、path または生成済みrun directoryを先に確認する。"
        return "probe audit が未指定または未生成のため、event refresh 前に public probe 証拠をauditする。"
    if cycle_status == "BLOCKED_PROBE_QUALITY":
        return "probe品質が不足しているため、raw refreshへ進まず public probe の欠損を修復する。"
    if cycle_status == "READY_FOR_RAW_REFRESH":
        return "probe audit は通過しているため、audit済みraw snapshotからlocal artifactを再生成できる。"
    if cycle_status == "RAW_REFRESH_NO_EVENT":
        return "raw refresh は完了したがevent候補がないため、無理にevent化せずknown gapsや閾値を確認する。"
    if cycle_status == "READY_FOR_DECISION":
        return "event候補があるため、outcomeを見る前にprospective decisionを記録する。"
    if cycle_status == "READY_FOR_OUTCOME_AFTER_MATURITY":
        return "decisionは記録済みのため、観察窓が成熟してからoutcomeを記録する。"
    if cycle_status == "READY_FOR_ROWS_PREVIEW":
        return "matured outcomeから3action rows previewを作れるが、actual cash evidenceではない点を残す。"
    if cycle_status == "READY_FOR_TOURNAMENT_REPORT":
        return "rows previewからtournament reportを作れるが、proxy gapをactual cashとして扱わない。"
    if cycle_status == "READY_FOR_TOURNAMENT_GATE":
        return (
            "tournament reportをgateに通し、tiny live承認準備へ進めるかをlocal artifactで判定する。"
        )
    if cycle_status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW":
        return "人間のtiny live承認準備に進める可能性があるが、live実行許可ではない。"
    if cycle_status == "NEEDS_ACTUAL_CASH":
        return "before-cost proxyやcash attribution不足があるため、actual cash basisへ作り直す。"
    if cycle_status == "NEEDS_MORE_EVIDENCE":
        return "event数や証拠が不足しているため、追加観測なしに勝ち筋へ進めない。"
    if cycle_status == "HOLD_NO_TRADE_LEADS":
        return "NO_TRADEが優位なため、trade実行ではなく見送り継続を基本に確認する。"
    return "条件違反または損失/集中リスクがあるため、event定義や仮説を修正または廃止する。"


def _next_steps(
    *,
    cycle_status: TruthCycleStatus,
    recommended_next_command: str,
    stop_reasons: list[str],
) -> list[TruthCycleNextStep]:
    steps: list[TruthCycleNextStep] = []
    if any(reason.endswith("_ARTIFACT_PATH_NOT_FOUND") for reason in stop_reasons):
        steps.append(
            TruthCycleNextStep(
                step_id="verify_artifact_path",
                purpose="指定したartifact pathまたはrun directoryが正しいかを確認する。",
                command="verify the specified artifact path before rerunning status",
            )
        )
    if cycle_status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW":
        steps.append(
            TruthCycleNextStep(
                step_id="human_tiny_live_approval",
                purpose="tiny live measurementへ進める前に別の明示承認を取る。",
                command="STOP_FOR_SEPARATE_HUMAN_APPROVAL",
                requires_explicit_approval=True,
            )
        )
        return steps
    if stop_reasons and cycle_status not in {
        "READY_FOR_RAW_REFRESH",
        "READY_FOR_DECISION",
        "READY_FOR_OUTCOME_AFTER_MATURITY",
        "READY_FOR_ROWS_PREVIEW",
        "READY_FOR_TOURNAMENT_REPORT",
        "READY_FOR_TOURNAMENT_GATE",
    }:
        steps.append(
            TruthCycleNextStep(
                step_id="resolve_stop_reasons",
                purpose="stop_reasonsを解消するまで次段階へ進めない。",
                command="inspect stop_reasons and fix the blocking evidence first",
            )
        )
    if recommended_next_command and recommended_next_command not in {
        "STOP_FOR_SEPARATE_HUMAN_APPROVAL",
        "REBUILD_WITH_ACTUAL_CASH",
    }:
        steps.append(
            TruthCycleNextStep(
                step_id="recommended_local_next_command",
                purpose="現在のartifact状態から見た次のlocal/read-only候補。",
                command=recommended_next_command,
            )
        )
    if cycle_status == "NEEDS_ACTUAL_CASH":
        steps.append(
            TruthCycleNextStep(
                step_id="rebuild_actual_cash_basis",
                purpose="before-cost proxyではなくactual cash evidenceでrows/report/gateを作り直す。",
                command="REBUILD_WITH_ACTUAL_CASH",
            )
        )
    return steps


_STAGE_INPUT_HINTS: dict[str, tuple[str | None, str]] = {
    "probe_audit": (
        "--probe-audit",
        "crypto_perp_probe_audit.v1 JSON from crypto-perp-probe-audit",
    ),
    "raw_refresh": (
        "--raw-refresh",
        "crypto_perp_raw_refresh.v1 JSON from crypto-perp-raw-refresh",
    ),
    "event": ("--event", "crypto_perp_event.v1 JSON from raw refresh event_paths"),
    "decision": ("--decision", "crypto_perp_decision.v1 JSON from crypto-perp-decision-record"),
    "outcome": ("--outcome", "crypto_perp_outcome.v1 JSON from crypto-perp-outcome-record"),
    "tournament_rows_preview": (
        "--rows-preview",
        "crypto_perp_tournament_rows_preview.v1 JSON from crypto-perp-tournament-rows-preview",
    ),
    "tournament_report": (
        "--tournament-report",
        "crypto_perp_tournament_report.v1 JSON from crypto-perp-tournament-report",
    ),
    "tournament_gate": (
        "--tournament-gate",
        "crypto_perp_tournament_gate.v1 JSON from crypto-perp-tournament-gate",
    ),
}


def _blocking_stage_id(
    *,
    cycle_status: TruthCycleStatus,
    event: dict[str, Any] | None,
) -> str | None:
    if cycle_status in {"MISSING_PROBE_AUDIT", "BLOCKED_PROBE_QUALITY"}:
        return "probe_audit"
    if cycle_status in {"READY_FOR_RAW_REFRESH", "RAW_REFRESH_NO_EVENT"}:
        return "raw_refresh"
    if cycle_status == "READY_FOR_DECISION":
        return "decision" if event is not None else "event"
    if cycle_status == "READY_FOR_OUTCOME_AFTER_MATURITY":
        return "outcome"
    if cycle_status == "READY_FOR_ROWS_PREVIEW":
        return "tournament_rows_preview"
    if cycle_status == "READY_FOR_TOURNAMENT_REPORT":
        return "tournament_report"
    if cycle_status == "READY_FOR_TOURNAMENT_GATE":
        return "tournament_gate"
    if cycle_status == "NEEDS_ACTUAL_CASH":
        return "outcome"
    if cycle_status in {"NEEDS_MORE_EVIDENCE", "HOLD_NO_TRADE_LEADS", "REVISE_OR_RETIRE"}:
        return "tournament_gate"
    return None


def _stage_checklist(
    *,
    stages: list[TruthCycleStage],
    cycle_status: TruthCycleStatus,
    event: dict[str, Any] | None,
) -> list[TruthCycleStageChecklistItem]:
    blocking_stage_id = _blocking_stage_id(cycle_status=cycle_status, event=event)
    checklist: list[TruthCycleStageChecklistItem] = []
    for stage in stages:
        expected_cli_option, expected_artifact_hint = _STAGE_INPUT_HINTS[stage.stage_id]
        checklist.append(
            TruthCycleStageChecklistItem(
                stage_id=stage.stage_id,
                status=stage.status,
                present=stage.present,
                blocks_progress=stage.status == "path_not_found"
                or stage.stage_id == blocking_stage_id,
                artifact_path=stage.artifact_path,
                expected_cli_option=expected_cli_option,
                expected_artifact_hint=expected_artifact_hint,
            )
        )
    return checklist


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
            return (
                cast(TruthCycleStatus, gate_status),
                str(tournament_gate.get("recommended_action") or ""),
                []
                if gate_status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
                else _gate_stop_reasons(tournament_gate, gate_status),
            )
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
    known_gaps = _known_gaps(
        probe_audit, raw_refresh, rows_preview, tournament_report, tournament_gate
    )
    stop_reasons = list(dict.fromkeys([*_missing_path_stop_reasons(stages), *stop_reasons]))
    summary = {
        "cycle_status": cycle_status,
        "human_summary": _human_summary(cycle_status, stop_reasons),
        "present_stage_count": sum(1 for stage in stages if stage.present),
        "missing_artifact_path_count": sum(
            1 for stage in stages if stage.status == "path_not_found"
        ),
        "known_gap_count": len(known_gaps),
        "stop_reason_count": len(stop_reasons),
    }
    next_steps = _next_steps(
        cycle_status=cycle_status,
        recommended_next_command=next_command,
        stop_reasons=stop_reasons,
    )
    stage_checklist = _stage_checklist(
        stages=stages,
        cycle_status=cycle_status,
        event=event,
    )
    summary["next_step_count"] = len(next_steps)
    summary["stage_checklist_blocker_count"] = sum(
        1 for item in stage_checklist if item.blocks_progress
    )
    return CryptoPerpTruthCycleStatus(
        artifact_id=stable_hash(
            [
                "crypto-perp-truth-cycle-status",
                summary,
                known_gaps,
                [step.model_dump(mode="json") for step in next_steps],
                [item.model_dump(mode="json") for item in stage_checklist],
            ]
        ),
        producer=CryptoPerpProducer(command=producer_command),
        cycle_status=cycle_status,
        recommended_next_command=next_command,
        next_steps=next_steps,
        stop_reasons=stop_reasons,
        stages=stages,
        stage_checklist=stage_checklist,
        known_gaps=known_gaps,
        summary=summary,
    )
