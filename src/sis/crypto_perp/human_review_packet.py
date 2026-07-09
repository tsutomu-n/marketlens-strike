from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Literal, cast

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


HUMAN_REVIEW_PACKET_SCHEMA_VERSION = "crypto_perp_human_review_packet.v1"
HUMAN_REVIEW_PACKET_PRODUCER = "crypto-perp-human-review-packet"

HumanReviewPacketDecision = Literal[
    "READY_FOR_HUMAN_REVIEW_PLANNING",
    "BLOCKED_BY_BOUNDARY_VIOLATION",
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


def _source_ref(path: Path) -> dict[str, str]:
    return {
        "path": path.as_posix(),
        "sha256": "sha256:" + stable_hash([path.read_text(encoding="utf-8")]),
    }


def _mapping(value: object) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return cast(Sequence[Any], value)
    return []


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(str(value))
    except ValueError:
        return default


def _bool(value: object) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(payload.get("summary"))


def _boundary_violation(payloads: Sequence[Mapping[str, Any]]) -> bool:
    forbidden = (
        "paper_permission_granted",
        "permits_paper_order",
        "permits_live_order",
        "actual_cash_used",
        "profit_proven",
        "wallet_used",
        "signing_used",
        "exchange_write_used",
        "live_order_submitted",
    )
    for payload in payloads:
        for key in forbidden:
            if _bool(payload.get(key)):
                return True
    return False


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
    ]


def _decide(
    *,
    boundary_violation: bool,
    gate_decision: str,
    kill_decision: str,
    top_next_action: str,
) -> tuple[HumanReviewPacketDecision, list[str]]:
    if boundary_violation:
        return "BLOCKED_BY_BOUNDARY_VIOLATION", ["BOUNDARY_FLAG_TRUE"]
    if gate_decision != "NO_CASH_BACKTEST_HOLD":
        return "BLOCKED_BY_GATE", ["NO_CASH_GATE_NOT_HOLD"]
    if kill_decision != "HOLD_FOR_LEADERBOARD":
        return "BLOCKED_BY_KILL_REPORT", ["NO_TRADE_KILL_REPORT_NOT_HOLD"]
    if top_next_action != "HOLD_FOR_HUMAN_REVIEW":
        return "BLOCKED_BY_LEADERBOARD", ["LEADERBOARD_TOP_ACTION_NOT_HUMAN_REVIEW"]
    return "READY_FOR_HUMAN_REVIEW_PLANNING", ["HUMAN_REVIEW_PACKET_READY"]


def build_human_review_packet(
    *,
    selection_manifest: Mapping[str, Any],
    decision: Mapping[str, Any],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    gate: Mapping[str, Any],
    kill_report: Mapping[str, Any],
    leaderboard: Mapping[str, Any],
    created_at: datetime | str,
    input_artifacts: Mapping[str, str],
    source_refs: Sequence[dict[str, str]],
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
    gate_decision = str(gate.get("gate_decision", "UNKNOWN"))
    kill_decision = str(kill_report.get("kill_decision", "UNKNOWN"))
    top_next_action = str(top_row.get("next_action", "UNKNOWN"))
    boundary_violation = _boundary_violation([gate, kill_report, leaderboard])
    packet_decision, reason_codes = _decide(
        boundary_violation=boundary_violation,
        gate_decision=gate_decision,
        kill_decision=kill_decision,
        top_next_action=top_next_action,
    )
    event_count = _int(gate_summary.get("event_count"), _int(decision.get("event_count")))
    outcome_count = _int(gate_summary.get("outcome_count"), _int(decision.get("outcome_count")))
    review_inputs = [
        {"name": name, "path": path, "required_for_review": True}
        for name, path in input_artifacts.items()
    ]
    current_evidence = {
        "candidate_decision": str(decision.get("decision", "UNKNOWN")),
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
        "pbo_status": str(gate_summary.get("pbo_status", decision_summary.get("pbo_status"))),
        "rolling_stability_status": str(gate_summary.get("rolling_stability_status", "UNKNOWN")),
        "backtest_total_result_usd": str(backtest_summary.get("total_result_usd", "0")),
        "stress_total_result_usd": str(stress_summary.get("total_result_usd", "0")),
        "strongest_evidence_level": str(evidence.get("strongest_evidence_level", "UNKNOWN")),
    }
    known_gaps = _known_gaps(selection_manifest, gate, kill_report, leaderboard)
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


def write_human_review_packet(
    *,
    selection_manifest_path: Path,
    decision_path: Path,
    backtest_path: Path,
    stress_path: Path,
    gate_path: Path,
    kill_report_path: Path,
    leaderboard_path: Path,
    out_dir: Path,
    created_at: datetime | str,
) -> HumanReviewPacketResult:
    selection_manifest = _read_json(selection_manifest_path)
    decision = _read_json(decision_path)
    backtest = _read_json(backtest_path)
    stress = _read_json(stress_path)
    gate = _read_json(gate_path)
    kill_report = _read_json(kill_report_path)
    leaderboard = _read_json(leaderboard_path)
    paths = {
        "selection_manifest": selection_manifest_path,
        "decision": decision_path,
        "backtest": backtest_path,
        "stress": stress_path,
        "gate": gate_path,
        "kill_report": kill_report_path,
        "leaderboard": leaderboard_path,
    }
    input_artifacts = {name: path.as_posix() for name, path in paths.items()}
    source_refs = [_source_ref(path) for path in paths.values()]
    payload = build_human_review_packet(
        selection_manifest=selection_manifest,
        decision=decision,
        backtest=backtest,
        stress=stress,
        gate=gate,
        kill_report=kill_report,
        leaderboard=leaderboard,
        created_at=created_at,
        input_artifacts=input_artifacts,
        source_refs=source_refs,
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
