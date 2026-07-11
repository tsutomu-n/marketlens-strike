from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Literal, cast

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.human_review_packet_validation import (
    EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES,
    _artifact_lineage_violations,
    _artifact_structure_violations,
    _boundary_violation,
    _int,
    _mapping,
    _sequence,
    _summary,
)
from sis.crypto_perp.io import file_artifact_ref, write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


HUMAN_REVIEW_PACKET_SCHEMA_VERSION = "crypto_perp_human_review_packet.v1"
HUMAN_REVIEW_PACKET_PRODUCER = "crypto-perp-human-review-packet"
HUMAN_REVIEW_INPUT_CONTRACT_VERSION = "crypto_perp_human_review_packet_inputs.v2"
_LINEAGE_VERIFIED_TOKEN = object()


HumanReviewPacketDecision = Literal[
    "READY_FOR_HUMAN_REVIEW_PLANNING",
    "BLOCKED_BY_BOUNDARY_VIOLATION",
    "BLOCKED_BY_ARTIFACT_LINEAGE",
    "BLOCKED_BY_CANDIDATE",
    "BLOCKED_BY_BIAS_GUARD",
    "BLOCKED_BY_PBO",
    "BLOCKED_BY_GATE",
    "BLOCKED_BY_KILL_REPORT",
    "BLOCKED_BY_LEADERBOARD",
]


@dataclass(frozen=True)
class HumanReviewPacketResult:
    payload: dict[str, Any]
    json_path: Path
    markdown_path: Path


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"expected JSON object in {path}:{line_number}")
        rows.append(row)
    return rows


def _source_ref(path: Path) -> dict[str, str]:
    return file_artifact_ref(path)


def _known_gaps(*payloads: Mapping[str, Any]) -> list[str]:
    gaps: list[str] = []
    for payload in payloads:
        values = _sequence(payload.get("known_gaps"))
        gaps.extend(str(value) for value in values)
    return list(dict.fromkeys(gaps))


def _review_questions() -> list[str]:
    return [
        "Are books/trades/replay gaps acceptable for planning Paper Observation, not execution?",
        "Is the NO_TRADE comparison sufficient for a planning discussion?",
        "Does the kill report keep the candidate alive after cost, stress, and concentration checks?",
        "Does the leaderboard keep the candidate at HOLD_FOR_HUMAN_REVIEW?",
        "Are drawdown and loss concentration acceptable for a no-cash local simulation candidate?",
        "Are the cost assumptions acceptable as no-cash simulation assumptions?",
        "Is any additional source coverage required before planning Paper Observation?",
        "Is each bias guard warning acceptable for planning, without treating it as execution readiness?",
    ]


def _decide(
    *,
    boundary_violation: bool,
    lineage_violations: Sequence[str],
    candidate_decision: str,
    bias_guard_status: str,
    bias_guard_stop_reasons: Sequence[str],
    pbo_status: str,
    pbo_evidence_verified: bool,
    gate_decision: str,
    kill_decision: str,
    top_next_action: str,
) -> tuple[HumanReviewPacketDecision, list[str]]:
    if boundary_violation:
        return "BLOCKED_BY_BOUNDARY_VIOLATION", ["BOUNDARY_FLAG_TRUE"]
    if lineage_violations:
        return "BLOCKED_BY_ARTIFACT_LINEAGE", list(dict.fromkeys(lineage_violations))
    if bias_guard_status != "PASS":
        status_reason = (
            "BIAS_GUARD_BLOCKED"
            if bias_guard_status == "BLOCKED"
            else "BIAS_GUARD_STATUS_MISSING_OR_UNKNOWN"
        )
        return "BLOCKED_BY_BIAS_GUARD", list(
            dict.fromkeys([status_reason, *bias_guard_stop_reasons])
        )
    if pbo_status != "COMPUTED_PASS":
        return "BLOCKED_BY_PBO", ["PBO_NOT_COMPUTED"]
    if not pbo_evidence_verified:
        return "BLOCKED_BY_PBO", ["PBO_COMPUTATION_EVIDENCE_MISSING"]
    if candidate_decision != "BACKTEST_CANDIDATE_HOLD":
        return "BLOCKED_BY_CANDIDATE", ["BACKTEST_CANDIDATE_NOT_HOLD"]
    if gate_decision != "NO_CASH_BACKTEST_HOLD":
        return "BLOCKED_BY_GATE", ["NO_CASH_GATE_NOT_HOLD"]
    if kill_decision != "HOLD_FOR_LEADERBOARD":
        return "BLOCKED_BY_KILL_REPORT", ["NO_TRADE_KILL_REPORT_NOT_HOLD"]
    if top_next_action != "HOLD_FOR_HUMAN_REVIEW":
        return "BLOCKED_BY_LEADERBOARD", ["LEADERBOARD_TOP_ACTION_NOT_HUMAN_REVIEW"]
    return "READY_FOR_HUMAN_REVIEW_PLANNING", ["HUMAN_REVIEW_PACKET_READY"]


def _build_human_review_packet(
    *,
    selection_manifest: Mapping[str, Any],
    decision: Mapping[str, Any],
    tournament_rows: Mapping[str, Any],
    bias_guard: Mapping[str, Any],
    data_availability: Mapping[str, Any],
    signal_rows: Sequence[Mapping[str, Any]],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    rolling_stability: Mapping[str, Any],
    gate: Mapping[str, Any],
    kill_report: Mapping[str, Any],
    leaderboard: Mapping[str, Any],
    created_at: datetime | str,
    input_artifacts: Mapping[str, str],
    source_refs: Sequence[dict[str, str]],
    lineage_violations: Sequence[str] = (),
    _lineage_token: object | None = None,
) -> dict[str, Any]:
    created = ensure_utc_aware("created_at", created_at)
    gate_summary = _summary(gate)
    decision_summary = _summary(decision)
    evidence = _mapping(decision.get("evidence_grade_summary"))
    backtest_summary = _summary(backtest)
    stress_summary = _summary(stress)
    selection_coverage = _mapping(selection_manifest.get("source_coverage"))
    leaderboard_rows = _sequence(leaderboard.get("rows"))
    top_row = _mapping(leaderboard_rows[0]) if leaderboard_rows else {}
    candidate_decision = str(decision.get("decision", "UNKNOWN"))
    gate_decision = str(gate.get("gate_decision", "UNKNOWN"))
    effective_bias_guard = bias_guard
    bias_guard_status = str(effective_bias_guard.get("guard_status", "missing"))
    pbo_status = str(effective_bias_guard.get("pbo_status", "missing"))
    bias_guard_stop_reasons = [
        str(value) for value in _sequence(effective_bias_guard.get("stop_reasons")) if value
    ]
    bias_guard_warning_codes = [
        str(value) for value in _sequence(decision_summary.get("bias_guard_warning_codes")) if value
    ]
    guard_warning_codes = [
        str(value)
        for value in _sequence(effective_bias_guard.get("known_gaps"))
        if str(value).startswith("BIAS_GUARD_WARNING_")
    ]
    bias_guard_warning_codes = list(
        dict.fromkeys([*bias_guard_warning_codes, *guard_warning_codes])
    )
    kill_decision = str(kill_report.get("kill_decision", "UNKNOWN"))
    top_next_action = str(top_row.get("next_action", "UNKNOWN"))
    boundary_violation = _boundary_violation(
        [
            selection_manifest,
            decision,
            tournament_rows,
            effective_bias_guard,
            data_availability,
            *signal_rows,
            backtest,
            stress,
            rolling_stability,
            gate,
            kill_report,
            leaderboard,
        ]
    )
    effective_lineage_violations = list(lineage_violations)
    expected_input_names = set(EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES)
    actual_input_names = set(input_artifacts)
    for name in sorted(expected_input_names - actual_input_names):
        effective_lineage_violations.append(f"HUMAN_REVIEW_INPUT_MISSING_{name.upper()}")
    for name in sorted(actual_input_names - expected_input_names):
        effective_lineage_violations.append(f"HUMAN_REVIEW_INPUT_UNEXPECTED_{name.upper()}")
    if _lineage_token is not _LINEAGE_VERIFIED_TOKEN:
        effective_lineage_violations.append("ARTIFACT_LINEAGE_NOT_VERIFIED")
    packet_decision, reason_codes = _decide(
        boundary_violation=boundary_violation,
        lineage_violations=effective_lineage_violations,
        candidate_decision=candidate_decision,
        bias_guard_status=bias_guard_status,
        bias_guard_stop_reasons=bias_guard_stop_reasons,
        pbo_status=pbo_status,
        pbo_evidence_verified=False,
        gate_decision=gate_decision,
        kill_decision=kill_decision,
        top_next_action=top_next_action,
    )
    if packet_decision != "READY_FOR_HUMAN_REVIEW_PLANNING":
        chain_reason_codes: list[str] = []
        for payload in (decision, gate, kill_report, top_row):
            chain_reason_codes.extend(
                str(value) for value in _sequence(payload.get("reason_codes")) if value
            )
        reason_codes = list(dict.fromkeys([*reason_codes, *chain_reason_codes]))
    event_count = _int(gate_summary.get("event_count"), _int(decision.get("event_count")))
    outcome_count = _int(gate_summary.get("outcome_count"), _int(decision.get("outcome_count")))
    ordered_input_names = [
        *(name for name in EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES if name in input_artifacts),
        *(name for name in sorted(input_artifacts) if name not in expected_input_names),
    ]
    review_inputs = [
        {"name": name, "path": input_artifacts[name], "required_for_review": True}
        for name in ordered_input_names
    ]
    current_evidence = {
        "candidate_decision": candidate_decision,
        "artifact_lineage_status": ("PASS" if not effective_lineage_violations else "BLOCKED"),
        "gate_decision": gate_decision,
        "kill_decision": kill_decision,
        "leaderboard_top_next_action": top_next_action,
        "event_count": event_count,
        "outcome_count": outcome_count,
        "ticker_available_count": _int(selection_coverage.get("ticker_available_count")),
        "funding_available_count": _int(selection_coverage.get("funding_available_count")),
        "critical_missing_count": _int(gate_summary.get("critical_missing_count")),
        "unknown_count": _int(gate_summary.get("unknown_count")),
        "executed_trade_count": _int(gate_summary.get("executed_trade_count")),
        "pbo_status": pbo_status,
        "pbo_computed": False,
        "pbo_evidence_verified": False,
        "bias_guard_status": bias_guard_status,
        "bias_guard_artifact_id": str(effective_bias_guard.get("artifact_id", "missing")),
        "bias_guard_warning_codes": bias_guard_warning_codes,
        "profit_robustness": _mapping(backtest_summary.get("profit_robustness")),
        "rolling_stability_status": str(gate_summary.get("rolling_stability_status", "UNKNOWN")),
        "backtest_total_result_usd": str(backtest_summary.get("total_result_usd", "0")),
        "stress_total_result_usd": str(stress_summary.get("total_result_usd", "0")),
        "strongest_evidence_level": str(evidence.get("strongest_evidence_level", "UNKNOWN")),
    }
    known_gaps = list(
        dict.fromkeys(
            [
                *_known_gaps(selection_manifest, data_availability, gate, kill_report, leaderboard),
                *bias_guard_warning_codes,
            ]
        )
    )
    summary = {
        "packet_decision": packet_decision,
        "ready_for_human_review_planning": packet_decision == "READY_FOR_HUMAN_REVIEW_PLANNING",
        "review_input_count": len(review_inputs),
        "known_gap_count": len(known_gaps),
        "gate_decision": gate_decision,
        "kill_decision": kill_decision,
        "top_next_action": top_next_action,
        "paper_permission_granted": False,
    }
    next_action = (
        "HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLANNING"
        if packet_decision == "READY_FOR_HUMAN_REVIEW_PLANNING"
        else "FIX_REVIEW_PACKET_BLOCKERS"
    )
    return {
        "schema_version": HUMAN_REVIEW_PACKET_SCHEMA_VERSION,
        "input_contract_version": HUMAN_REVIEW_INPUT_CONTRACT_VERSION,
        "artifact_id": stable_hash(
            ["human-review-packet", serialize_utc_z(created), packet_decision, current_evidence]
        ),
        "created_at": serialize_utc_z(created),
        "producer": CryptoPerpProducer(command=HUMAN_REVIEW_PACKET_PRODUCER).model_dump(
            mode="json"
        ),
        "source_refs": list(source_refs),
        "boundary": CryptoPerpBoundary().model_dump(mode="json"),
        "input_artifacts": dict(input_artifacts),
        "packet_decision": packet_decision,
        "reason_codes": reason_codes,
        "review_inputs": review_inputs,
        "current_evidence": current_evidence,
        "review_questions": _review_questions(),
        "known_gaps": known_gaps,
        "required_human_review": True,
        "next_action": next_action,
        "summary": summary,
        "paper_permission_granted": False,
        "permits_paper_order": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def build_human_review_packet(
    *,
    selection_manifest: Mapping[str, Any],
    decision: Mapping[str, Any],
    tournament_rows: Mapping[str, Any],
    bias_guard: Mapping[str, Any],
    data_availability: Mapping[str, Any],
    signal_rows: Sequence[Mapping[str, Any]],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    rolling_stability: Mapping[str, Any],
    gate: Mapping[str, Any],
    kill_report: Mapping[str, Any],
    leaderboard: Mapping[str, Any],
    created_at: datetime | str,
    input_artifacts: Mapping[str, str],
    source_refs: Sequence[dict[str, str]],
    lineage_violations: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a fail-closed packet without granting artifact-lineage trust."""
    return _build_human_review_packet(
        selection_manifest=selection_manifest,
        decision=decision,
        tournament_rows=tournament_rows,
        bias_guard=bias_guard,
        data_availability=data_availability,
        signal_rows=signal_rows,
        backtest=backtest,
        stress=stress,
        rolling_stability=rolling_stability,
        gate=gate,
        kill_report=kill_report,
        leaderboard=leaderboard,
        created_at=created_at,
        input_artifacts=input_artifacts,
        source_refs=source_refs,
        lineage_violations=lineage_violations,
    )


def write_human_review_packet(
    *,
    selection_manifest_path: Path,
    decision_path: Path,
    tournament_rows_path: Path,
    bias_guard_path: Path,
    data_availability_path: Path,
    signal_rows_path: Path,
    backtest_path: Path,
    stress_path: Path,
    rolling_stability_path: Path,
    gate_path: Path,
    kill_report_path: Path,
    leaderboard_path: Path,
    out_dir: Path,
    created_at: datetime | str,
) -> HumanReviewPacketResult:
    selection_manifest = _read_json(selection_manifest_path)
    decision = _read_json(decision_path)
    tournament_rows = _read_json(tournament_rows_path)
    bias_guard = _read_json(bias_guard_path)
    data_availability = _read_json(data_availability_path)
    signal_rows = _read_jsonl(signal_rows_path)
    backtest = _read_json(backtest_path)
    stress = _read_json(stress_path)
    rolling_stability = _read_json(rolling_stability_path)
    gate = _read_json(gate_path)
    kill_report = _read_json(kill_report_path)
    leaderboard = _read_json(leaderboard_path)
    paths = {
        "selection_manifest": selection_manifest_path,
        "decision": decision_path,
        "tournament_rows": tournament_rows_path,
        "bias_guard": bias_guard_path,
        "data_availability": data_availability_path,
        "signal_rows": signal_rows_path,
        "backtest": backtest_path,
        "stress": stress_path,
        "rolling_stability": rolling_stability_path,
        "gate": gate_path,
        "kill_report": kill_report_path,
        "leaderboard": leaderboard_path,
    }
    input_artifacts = {name: path.as_posix() for name, path in paths.items()}
    source_refs = [_source_ref(path) for path in paths.values()]
    lineage_violations = _artifact_structure_violations(
        selection_manifest=selection_manifest,
        decision=decision,
        tournament_rows=tournament_rows,
        bias_guard=bias_guard,
        data_availability=data_availability,
        signal_rows=signal_rows,
        backtest=backtest,
        stress=stress,
        rolling_stability=rolling_stability,
        gate=gate,
        kill_report=kill_report,
        leaderboard=leaderboard,
    )
    lineage_violations.extend(
        _artifact_lineage_violations(
            selection_manifest=selection_manifest,
            decision=decision,
            tournament_rows=tournament_rows,
            bias_guard=bias_guard,
            data_availability=data_availability,
            signal_rows=signal_rows,
            backtest=backtest,
            stress=stress,
            rolling_stability=rolling_stability,
            gate=gate,
            kill_report=kill_report,
            leaderboard=leaderboard,
            selection_manifest_path=selection_manifest_path,
            decision_path=decision_path,
            tournament_rows_path=tournament_rows_path,
            bias_guard_path=bias_guard_path,
            data_availability_path=data_availability_path,
            signal_rows_path=signal_rows_path,
            backtest_path=backtest_path,
            stress_path=stress_path,
            rolling_stability_path=rolling_stability_path,
            gate_path=gate_path,
            kill_report_path=kill_report_path,
        )
    )
    payload = _build_human_review_packet(
        selection_manifest=selection_manifest,
        decision=decision,
        backtest=backtest,
        tournament_rows=tournament_rows,
        bias_guard=bias_guard,
        data_availability=data_availability,
        signal_rows=signal_rows,
        stress=stress,
        rolling_stability=rolling_stability,
        gate=gate,
        kill_report=kill_report,
        leaderboard=leaderboard,
        created_at=created_at,
        input_artifacts=input_artifacts,
        source_refs=source_refs,
        lineage_violations=lineage_violations,
        _lineage_token=_LINEAGE_VERIFIED_TOKEN,
    )
    json_path = out_dir / "human_review_packet.json"
    markdown_path = out_dir / "human_review_packet.md"
    write_json_artifact(json_path, payload)
    write_text_artifact(markdown_path, _render_markdown(payload))
    return HumanReviewPacketResult(
        payload=payload, json_path=json_path, markdown_path=markdown_path
    )


def _render_markdown(payload: Mapping[str, Any]) -> str:
    evidence = _mapping(payload["current_evidence"])
    questions = cast(Sequence[str], payload["review_questions"])
    gaps = cast(Sequence[str], payload["known_gaps"])
    lines = [
        "# Crypto Perp Human Review Packet",
        "",
        f"- packet_decision: `{payload['packet_decision']}`",
        f"- next_action: `{payload['next_action']}`",
        f"- gate_decision: `{evidence['gate_decision']}`",
        f"- kill_decision: `{evidence['kill_decision']}`",
        f"- leaderboard_top_next_action: `{evidence['leaderboard_top_next_action']}`",
        f"- event_count: `{evidence['event_count']}`",
        f"- outcome_count: `{evidence['outcome_count']}`",
        f"- executed_trade_count: `{evidence['executed_trade_count']}`",
        f"- pbo_status: `{evidence['pbo_status']}`",
        f"- bias_guard_status: `{evidence['bias_guard_status']}`",
        f"- rolling_stability_status: `{evidence['rolling_stability_status']}`",
        "- paper_permission_granted: `false`",
        "- permits_paper_order: `false`",
        "- actual_cash_used: `false`",
        "- profit_proven: `false`",
        "",
        "## Known Gaps",
        "",
        *(f"- `{gap}`" for gap in gaps),
        "",
        "## Review Questions",
        "",
        *(f"{index}. {question}" for index, question in enumerate(questions, start=1)),
        "",
        "This packet is a no-cash human review input. It does not start Paper Observation, grant paper order permission, prove profit, use actual cash, or permit live orders.",
    ]
    return "\n".join(lines)
