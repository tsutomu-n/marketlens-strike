from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Literal, cast

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


CANDIDATE_LEADERBOARD_SCHEMA_VERSION = "crypto_perp_candidate_leaderboard.v1"
CANDIDATE_LEADERBOARD_PRODUCER = "crypto-perp-candidate-leaderboard"

CandidateNextAction = Literal["KILL", "REVISE_SIGNAL", "COLLECT_MORE_DATA", "HOLD_FOR_HUMAN_REVIEW"]


@dataclass(frozen=True)
class CandidateLeaderboardResult:
    payload: dict[str, Any]
    json_path: Path
    markdown_path: Path


def _decimal(value: object, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(str(value))
    except ValueError:
        return default


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object rows in {path}")
        rows.append(payload)
    return rows


def _source_ref(path: Path) -> dict[str, str]:
    return {
        "path": path.as_posix(),
        "sha256": "sha256:" + stable_hash([path.read_text(encoding="utf-8")]),
    }


def _mapping(value: object) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}


def _summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(payload.get("summary"))


def _candidate_id(decision: Mapping[str, Any]) -> str:
    for key in ("pack_id", "artifact_id"):
        value = decision.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return stable_hash(["candidate", decision])


def _next_action(kill_decision: str) -> CandidateNextAction:
    if kill_decision.startswith("KILL_"):
        return "KILL"
    if kill_decision == "COLLECT_MORE_DATA":
        return "COLLECT_MORE_DATA"
    if kill_decision == "HOLD_FOR_LEADERBOARD":
        return "HOLD_FOR_HUMAN_REVIEW"
    return "REVISE_SIGNAL"


def _source_quality_score(decision: Mapping[str, Any], gate: Mapping[str, Any]) -> Decimal:
    evidence = _mapping(decision.get("evidence_grade_summary"))
    critical_missing = _int(evidence.get("critical_missing_count"))
    event_count = max(
        1, _int(evidence.get("event_count"), _int(_summary(gate).get("event_count"), 1))
    )
    source_missing = _mapping(evidence.get("source_missing_counts"))
    critical_penalty = min(Decimal("1"), Decimal(critical_missing) / Decimal(event_count))
    optional_missing = sum(_int(value) for value in source_missing.values())
    optional_penalty = min(Decimal("0.25"), Decimal(optional_missing) / Decimal(event_count * 20))
    score = Decimal("1") - critical_penalty - optional_penalty
    return max(Decimal("0"), score)


def _ranking_score(
    *,
    next_action: CandidateNextAction,
    source_quality_score: Decimal,
    stress_total: Decimal,
    no_trade_delta: Decimal,
    executed_trade_count: int,
    max_drawdown: Decimal,
    loss_concentration: Decimal,
    profit_concentration: Decimal,
) -> Decimal:
    if next_action == "KILL":
        return Decimal("0")
    if next_action == "COLLECT_MORE_DATA":
        return Decimal("10")
    if next_action == "REVISE_SIGNAL":
        return Decimal("25")
    score = Decimal("50")
    score += source_quality_score * Decimal("20")
    score += min(Decimal("10"), max(Decimal("0"), no_trade_delta))
    score += min(Decimal("5"), max(Decimal("0"), stress_total))
    score += min(Decimal("10"), Decimal(executed_trade_count) / Decimal("2"))
    score -= min(Decimal("10"), abs(max_drawdown))
    score -= loss_concentration * Decimal("10")
    score -= profit_concentration * Decimal("5")
    return max(Decimal("0"), score)


def _symbol(signal_rows: Sequence[Mapping[str, Any]] | None) -> str:
    if not signal_rows:
        return "unknown"
    value = signal_rows[0].get("symbol")
    return str(value) if value is not None else "unknown"


def _selected_action_family(signal_rows: Sequence[Mapping[str, Any]] | None) -> str:
    if not signal_rows:
        return "unknown"
    actions = sorted({str(row.get("selected_action", "UNKNOWN")) for row in signal_rows})
    return "+".join(actions)


def build_candidate_leaderboard(
    *,
    decision: Mapping[str, Any],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    kill_report: Mapping[str, Any],
    gate: Mapping[str, Any],
    created_at: datetime | str,
    input_artifacts: Mapping[str, str],
    source_refs: Sequence[dict[str, str]],
    signal_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    created = ensure_utc_aware("created_at", created_at)
    backtest_summary = _summary(backtest)
    stress_summary = _summary(stress)
    gate_summary = _summary(gate)
    kill_decision = str(kill_report.get("kill_decision", "REVISE_SOURCE_OR_SIGNAL"))
    next_action = _next_action(kill_decision)
    source_score = _source_quality_score(decision, gate)
    no_trade_delta = _decimal(
        kill_report.get("cost_adjusted_delta_vs_no_trade"),
        _decimal(backtest_summary.get("total_result_usd")),
    )
    stress_total = _decimal(
        kill_report.get("stress_delta_vs_no_trade"),
        _decimal(stress_summary.get("total_result_usd")),
    )
    executed_trade_count = _int(backtest_summary.get("executed_trade_count"))
    max_drawdown = _decimal(backtest_summary.get("max_drawdown_usd"))
    loss_concentration = _decimal(kill_report.get("largest_loss_concentration"))
    profit_concentration = _decimal(kill_report.get("largest_win_concentration"))
    ranking_score = _ranking_score(
        next_action=next_action,
        source_quality_score=source_score,
        stress_total=stress_total,
        no_trade_delta=no_trade_delta,
        executed_trade_count=executed_trade_count,
        max_drawdown=max_drawdown,
        loss_concentration=loss_concentration,
        profit_concentration=profit_concentration,
    )
    reason_codes = (
        list(kill_report.get("reason_codes", []))
        if isinstance(kill_report.get("reason_codes"), list)
        else []
    )
    known_gaps = list(
        dict.fromkeys(
            [
                *(
                    kill_report.get("known_gaps", [])
                    if isinstance(kill_report.get("known_gaps"), list)
                    else []
                ),
                *(gate.get("known_gaps", []) if isinstance(gate.get("known_gaps"), list) else []),
            ]
        )
    )
    row = {
        "rank": 1,
        "candidate_id": _candidate_id(decision),
        "symbol": _symbol(signal_rows),
        "timeframe": "5m",
        "family": _selected_action_family(signal_rows),
        "setup_type": "active_no_cash_hold",
        "ranking_score": str(ranking_score),
        "source_quality_score": str(source_score),
        "cost_adjusted_total": str(backtest_summary.get("total_result_usd", "0")),
        "stress_total": str(stress_summary.get("total_result_usd", "0")),
        "no_trade_delta": str(no_trade_delta),
        "executed_trade_count": executed_trade_count,
        "win_rate": backtest_summary.get("win_rate"),
        "payoff_ratio": None,
        "max_drawdown": str(max_drawdown),
        "loss_concentration": str(loss_concentration),
        "profit_concentration": str(profit_concentration),
        "pbo_status": _summary(decision).get("pbo_status"),
        "rolling_stability_status": gate_summary.get("rolling_stability_status"),
        "gate_decision": gate.get("gate_decision"),
        "kill_decision": kill_decision,
        "next_action": next_action,
        "reason_codes": reason_codes,
        "known_gaps": known_gaps,
    }
    payload = {
        "schema_version": CANDIDATE_LEADERBOARD_SCHEMA_VERSION,
        "artifact_id": stable_hash(["candidate-leaderboard", serialize_utc_z(created), row]),
        "created_at": serialize_utc_z(created),
        "producer": CryptoPerpProducer(command=CANDIDATE_LEADERBOARD_PRODUCER).model_dump(
            mode="json"
        ),
        "source_refs": list(source_refs),
        "boundary": CryptoPerpBoundary().model_dump(mode="json"),
        "input_artifacts": dict(input_artifacts),
        "rows": [row],
        "summary": {
            "row_count": 1,
            "top_candidate_id": row["candidate_id"],
            "top_next_action": next_action,
            "top_kill_decision": kill_decision,
            "paper_permission_granted": False,
        },
        "known_gaps": known_gaps,
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
    return payload


def write_candidate_leaderboard(
    *,
    decision_path: Path,
    backtest_path: Path,
    stress_path: Path,
    kill_report_path: Path,
    gate_path: Path,
    out_dir: Path,
    created_at: datetime | str,
    signal_rows_path: Path | None = None,
) -> CandidateLeaderboardResult:
    decision = _read_json(decision_path)
    backtest = _read_json(backtest_path)
    stress = _read_json(stress_path)
    kill_report = _read_json(kill_report_path)
    gate = _read_json(gate_path)
    signal_rows = _read_jsonl(signal_rows_path) if signal_rows_path is not None else None
    refs = [
        _source_ref(decision_path),
        _source_ref(backtest_path),
        _source_ref(stress_path),
        _source_ref(kill_report_path),
        _source_ref(gate_path),
    ]
    input_artifacts = {
        "decision": decision_path.as_posix(),
        "backtest": backtest_path.as_posix(),
        "stress": stress_path.as_posix(),
        "kill_report": kill_report_path.as_posix(),
        "gate": gate_path.as_posix(),
    }
    if signal_rows_path is not None:
        refs.append(_source_ref(signal_rows_path))
        input_artifacts["signal_rows"] = signal_rows_path.as_posix()
    payload = build_candidate_leaderboard(
        decision=decision,
        backtest=backtest,
        stress=stress,
        kill_report=kill_report,
        gate=gate,
        signal_rows=signal_rows,
        created_at=created_at,
        input_artifacts=input_artifacts,
        source_refs=refs,
    )
    json_path = out_dir / "candidate_leaderboard.json"
    markdown_path = out_dir / "candidate_leaderboard.md"
    write_json_artifact(json_path, payload)
    write_text_artifact(markdown_path, _render_markdown(payload))
    return CandidateLeaderboardResult(
        payload=payload, json_path=json_path, markdown_path=markdown_path
    )


def _render_markdown(payload: Mapping[str, Any]) -> str:
    rows = cast(Sequence[Mapping[str, Any]], payload["rows"])
    top = rows[0]
    return "\n".join(
        [
            "# Candidate Leaderboard",
            "",
            f"- row_count: `{len(rows)}`",
            f"- top_candidate_id: `{top['candidate_id']}`",
            f"- top_next_action: `{top['next_action']}`",
            f"- top_kill_decision: `{top['kill_decision']}`",
            f"- ranking_score: `{top['ranking_score']}`",
            "- paper_permission_granted: `false`",
            "- permits_paper_order: `false`",
            "- actual_cash_used: `false`",
            "",
            "This leaderboard is a no-cash human review aid. It does not grant Paper Observation permission, prove profit, or use actual cash.",
        ]
    )
