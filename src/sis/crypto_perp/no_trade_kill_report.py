from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import ValidationError

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.io import file_artifact_ref, write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.no_cash_backtest_gate import NoCashBacktestGateArtifact
from sis.crypto_perp.tournament_rows import CryptoPerpTournamentRowsV2


NO_TRADE_KILL_REPORT_SCHEMA_VERSION = "crypto_perp_no_trade_kill_report.v1"
NO_TRADE_KILL_REPORT_PRODUCER = "crypto-perp-no-trade-kill-report"
MIN_EVENTS_FOR_REVIEW = 30
MIN_EXECUTED_TRADES_FOR_REVIEW = 10
MAX_LARGEST_LOSS_TO_TOTAL_RESULT_RATIO = Decimal("0.5")
MAX_LARGEST_WIN_CONCENTRATION = Decimal("0.6")
MAX_TOP2_WIN_CONCENTRATION = Decimal("0.8")

NoTradeKillDecision = Literal[
    "KILL_NO_TRADE_LEADER",
    "KILL_AFTER_COST_NEGATIVE",
    "KILL_STRESS_NEGATIVE",
    "KILL_LOSS_CONCENTRATION",
    "KILL_UPSTREAM_GATE_REJECTED",
    "REVISE_SOURCE_OR_SIGNAL",
    "COLLECT_MORE_DATA",
    "HOLD_FOR_LEADERBOARD",
]


@dataclass(frozen=True)
class NoTradeKillReportResult:
    payload: dict[str, Any]
    json_path: Path
    markdown_path: Path


def _decimal(value: object, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


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
    return file_artifact_ref(path)


def _validate_public_gate(gate: Mapping[str, Any]) -> dict[str, Any]:
    try:
        artifact = NoCashBacktestGateArtifact.model_validate(gate)
    except ValidationError as exc:
        raise ValueError(f"gate artifact is invalid: {exc}") from exc
    return artifact.model_dump(mode="json")


def _validate_public_tournament_rows(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        artifact = CryptoPerpTournamentRowsV2.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("tournament_rows artifact is invalid") from exc
    totals = {
        action: sum(
            (row.cost_adjusted_cash_estimate_usd for row in artifact.rows if row.action == action),
            Decimal("0"),
        )
        for action in ("REVERSAL_SHORT", "CONTINUATION_LONG", "NO_TRADE")
    }
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    derived_leader = None if ordered[0][1] == ordered[1][1] else ordered[0][0]
    if artifact.summary.get("leader_action") != derived_leader:
        raise ValueError("tournament_rows leader_action does not match derived rows")
    return artifact.model_dump(mode="json")


def _summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("summary")
    return cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}


def _results(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = payload.get("results")
    return [cast(Mapping[str, Any], row) for row in value] if isinstance(value, list) else []


def _selected_action_counts(signal_rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(row.get("selected_action", "UNKNOWN")) for row in signal_rows))


def _positive_concentration(values: Sequence[Decimal]) -> tuple[Decimal, Decimal]:
    positives = sorted((value for value in values if value > 0), reverse=True)
    total_positive = sum(positives, Decimal("0"))
    if total_positive <= 0:
        return Decimal("0"), Decimal("0")
    return positives[0] / total_positive, sum(positives[:2], Decimal("0")) / total_positive


def _decimal_sequence(value: object) -> list[Decimal] | None:
    if not isinstance(value, list) or not value:
        return None
    parsed: list[Decimal] = []
    for item in value:
        try:
            parsed.append(Decimal(str(item)))
        except (InvalidOperation, ValueError):
            return None
    return parsed


def _derived_episode_totals(
    results: Sequence[Mapping[str, Any]],
    tournament_rows: Mapping[str, Any] | None,
) -> list[Decimal] | None:
    if tournament_rows is None:
        return None
    windows = _tournament_summary(tournament_rows).get("execution_windows")
    if not isinstance(windows, Mapping):
        return None
    executed = [row for row in results if row.get("fill_status") == "simulated"]
    ordered: list[tuple[datetime, datetime, str, Decimal]] = []
    seen_event_ids: set[str] = set()
    for row in executed:
        event_id = str(row.get("event_id", ""))
        if not event_id or event_id in seen_event_ids:
            return None
        seen_event_ids.add(event_id)
        window = windows.get(event_id)
        if not isinstance(window, Mapping):
            return None
        try:
            entry_at = ensure_utc_aware("entry_at", str(window.get("entry_at")))
            settled_at = ensure_utc_aware("settled_at", str(window.get("settled_at")))
            value = Decimal(str(row.get("result_usd")))
        except (InvalidOperation, TypeError, ValueError):
            return None
        if entry_at >= settled_at:
            return None
        ordered.append((entry_at, settled_at, event_id, value))
    if not ordered:
        return None
    ordered.sort(key=lambda item: (item[0], item[2]))
    totals: list[Decimal] = []
    cluster_end: datetime | None = None
    for entry_at, settled_at, _, value in ordered:
        if cluster_end is None or entry_at >= cluster_end:
            totals.append(value)
            cluster_end = settled_at
        else:
            totals[-1] += value
            cluster_end = max(cluster_end, settled_at)
    return totals


def _loss_concentration(values: Sequence[Decimal]) -> tuple[Decimal, Decimal]:
    losses = sorted((abs(value) for value in values if value < 0), reverse=True)
    total_loss = sum(losses, Decimal("0"))
    if total_loss <= 0:
        return Decimal("0"), Decimal("0")
    return losses[0] / total_loss, total_loss


def _largest_loss_to_total_result(values: Sequence[Decimal], total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal("0")
    losses = [abs(value) for value in values if value < 0]
    if not losses:
        return Decimal("0")
    return max(losses) / total


def _tournament_summary(tournament_rows: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if tournament_rows is None:
        return {}
    value = tournament_rows.get("summary")
    return cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}


def _selected_tournament_costs(
    *,
    signal_rows: Sequence[Mapping[str, Any]],
    tournament_rows: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    if tournament_rows is None:
        return {"fee_drag": None, "funding_drag": None, "slippage_drag": None}
    rows = tournament_rows.get("rows")
    if not isinstance(rows, list):
        return {"fee_drag": None, "funding_drag": None, "slippage_drag": None}
    selected = {
        (str(row.get("event_id")), str(row.get("selected_action")))
        for row in signal_rows
        if str(row.get("selected_action")) not in {"NO_TRADE", "UNKNOWN"}
    }
    fee = Decimal("0")
    funding = Decimal("0")
    slippage = Decimal("0")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        key = (str(row.get("event_id")), str(row.get("action")))
        if key not in selected:
            continue
        fee += _decimal(row.get("fee_estimate_usd"))
        funding += _decimal(row.get("funding_estimate_usd"))
        slippage += _decimal(row.get("slippage_estimate_usd"))
    return {"fee_drag": str(fee), "funding_drag": str(funding), "slippage_drag": str(slippage)}


def _decide(
    *,
    event_count: int,
    executed_trade_count: int,
    unknown_count: int,
    blocked_missing_action_row_count: int,
    cost_adjusted_delta_vs_no_trade: Decimal,
    stress_delta_vs_no_trade: Decimal,
    beats_no_trade: bool,
    tournament_leader_action: str | None,
    largest_loss_to_total_result_ratio: Decimal,
    largest_win_concentration: Decimal,
    top2_win_concentration: Decimal,
    episode_concentration_estimated: bool,
    episode_largest_win_concentration: Decimal,
    episode_top2_win_concentration: Decimal,
) -> tuple[NoTradeKillDecision, list[str]]:
    if event_count < MIN_EVENTS_FOR_REVIEW or executed_trade_count < MIN_EXECUTED_TRADES_FOR_REVIEW:
        return "COLLECT_MORE_DATA", ["MIN_REVIEW_SAMPLE_NOT_MET"]
    if unknown_count > 0 or blocked_missing_action_row_count > 0:
        return "REVISE_SOURCE_OR_SIGNAL", ["UNKNOWN_OR_BLOCKED_SIGNAL_ROWS_PRESENT"]
    if tournament_leader_action is None:
        return "COLLECT_MORE_DATA", ["TOURNAMENT_LEADER_NOT_ESTIMABLE"]
    if tournament_leader_action == "NO_TRADE":
        return "KILL_NO_TRADE_LEADER", ["TOURNAMENT_LEADER_NO_TRADE"]
    if not beats_no_trade or cost_adjusted_delta_vs_no_trade <= 0:
        return "KILL_AFTER_COST_NEGATIVE", ["NO_TRADE_NOT_BEATEN_AFTER_COST"]
    if stress_delta_vs_no_trade <= 0:
        return "KILL_STRESS_NEGATIVE", ["STRESS_RESULT_NOT_POSITIVE"]
    if largest_loss_to_total_result_ratio > MAX_LARGEST_LOSS_TO_TOTAL_RESULT_RATIO:
        return "KILL_LOSS_CONCENTRATION", ["LOSS_CONCENTRATION_TOO_HIGH"]
    if (
        largest_win_concentration > MAX_LARGEST_WIN_CONCENTRATION
        or top2_win_concentration > MAX_TOP2_WIN_CONCENTRATION
    ):
        return "REVISE_SOURCE_OR_SIGNAL", ["PROFIT_CONCENTRATION_HIGH"]
    if not episode_concentration_estimated:
        return "COLLECT_MORE_DATA", ["EPISODE_PROFIT_CONCENTRATION_NOT_ESTIMABLE"]
    if (
        episode_largest_win_concentration > MAX_LARGEST_WIN_CONCENTRATION
        or episode_top2_win_concentration > MAX_TOP2_WIN_CONCENTRATION
    ):
        return "REVISE_SOURCE_OR_SIGNAL", ["EPISODE_PROFIT_CONCENTRATION_HIGH"]
    return "HOLD_FOR_LEADERBOARD", ["NO_TRADE_KILL_REPORT_HOLD_FOR_LEADERBOARD"]


def build_no_trade_kill_report(
    *,
    signal_rows: Sequence[Mapping[str, Any]],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    gate: Mapping[str, Any] | None,
    created_at: datetime | str,
    input_artifacts: Mapping[str, str],
    source_refs: Sequence[dict[str, str]],
    tournament_rows: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    created = ensure_utc_aware("created_at", created_at)
    backtest_summary = _summary(backtest)
    stress_summary = _summary(stress)
    backtest_results = _results(backtest)
    values = [_decimal(row.get("result_usd")) for row in backtest_results]
    total = _decimal(backtest_summary.get("total_result_usd"))
    stress_total = _decimal(stress_summary.get("total_result_usd"))
    event_count = _int(backtest_summary.get("event_count"), len(backtest_results))
    executed_trade_count = _int(backtest_summary.get("executed_trade_count"))
    no_trade_count = _int(backtest_summary.get("no_trade_count"))
    unknown_count = _int(backtest_summary.get("unknown_count"))
    blocked_missing_action_row_count = _int(
        backtest_summary.get("blocked_missing_action_row_count")
    )
    beats_no_trade = bool(backtest_summary.get("beats_no_trade"))
    largest_win_concentration, top2_win_concentration = _positive_concentration(values)
    robustness = backtest_summary.get("profit_robustness")
    robustness_summary = (
        cast(Mapping[str, Any], robustness) if isinstance(robustness, Mapping) else {}
    )
    reported_episode_values = _decimal_sequence(robustness_summary.get("market_episode_totals_usd"))
    derived_episode_values = _derived_episode_totals(backtest_results, tournament_rows)
    episode_values = (
        derived_episode_values
        if derived_episode_values is not None and reported_episode_values == derived_episode_values
        else None
    )
    episode_concentration_estimated = episode_values is not None
    episode_largest_win_concentration, episode_top2_win_concentration = (
        _positive_concentration(episode_values)
        if episode_values is not None
        else (Decimal("0"), Decimal("0"))
    )
    largest_loss_concentration, total_loss = _loss_concentration(values)
    largest_loss_to_total_result_ratio = _largest_loss_to_total_result(values, total)
    tournament = _tournament_summary(tournament_rows)
    tournament_leader_action = (
        str(tournament.get("leader_action"))
        if tournament.get("leader_action") is not None
        else None
    )
    local_decision, local_reason_codes = _decide(
        event_count=event_count,
        executed_trade_count=executed_trade_count,
        unknown_count=unknown_count,
        blocked_missing_action_row_count=blocked_missing_action_row_count,
        cost_adjusted_delta_vs_no_trade=total,
        stress_delta_vs_no_trade=stress_total,
        beats_no_trade=beats_no_trade,
        tournament_leader_action=tournament_leader_action,
        largest_loss_to_total_result_ratio=largest_loss_to_total_result_ratio,
        largest_win_concentration=largest_win_concentration,
        top2_win_concentration=top2_win_concentration,
        episode_concentration_estimated=episode_concentration_estimated,
        episode_largest_win_concentration=episode_largest_win_concentration,
        episode_top2_win_concentration=episode_top2_win_concentration,
    )
    gate_payload = gate or {}
    upstream_gate_decision = str(gate_payload.get("gate_decision", "UNKNOWN"))
    upstream_reason_codes = [str(value) for value in gate_payload.get("reason_codes", []) if value]
    upstream_blockers = [
        dict(value) for value in gate_payload.get("blockers", []) if isinstance(value, Mapping)
    ]
    if upstream_gate_decision == "NO_CASH_BACKTEST_REJECT":
        kill_decision = "KILL_UPSTREAM_GATE_REJECTED"
        reason_codes = _unique(["UPSTREAM_GATE_REJECTED", *upstream_reason_codes])
    elif upstream_gate_decision == "NO_CASH_BACKTEST_REVISE":
        kill_decision = "REVISE_SOURCE_OR_SIGNAL"
        reason_codes = _unique(["UPSTREAM_GATE_REVISE", *upstream_reason_codes])
    elif upstream_gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA":
        kill_decision = "COLLECT_MORE_DATA"
        reason_codes = _unique(["UPSTREAM_GATE_COLLECT_MORE_DATA", *upstream_reason_codes])
    elif upstream_gate_decision == "NO_CASH_BACKTEST_HOLD":
        kill_decision = local_decision
        reason_codes = local_reason_codes
    else:
        kill_decision = "COLLECT_MORE_DATA"
        reason_codes = _unique(["UPSTREAM_GATE_MISSING_OR_UNKNOWN", *upstream_reason_codes])
    known_gaps = [
        "LOCAL_SIMULATION_ONLY",
        "NOT_ACTUAL_CASH",
        "NOT_LIVE_READINESS",
        "PAPER_PERMISSION_NOT_GRANTED",
    ]
    if tournament_rows is None:
        known_gaps.append("TOURNAMENT_ROWS_NOT_PROVIDED_FOR_COST_DRAG_BREAKDOWN")
    cost_breakdown = _selected_tournament_costs(
        signal_rows=signal_rows,
        tournament_rows=tournament_rows,
    )
    summary = {
        "event_count": event_count,
        "executed_trade_count": executed_trade_count,
        "no_trade_count": no_trade_count,
        "unknown_count": unknown_count,
        "blocked_missing_action_row_count": blocked_missing_action_row_count,
        "cost_adjusted_total_result_usd": str(total),
        "stress_total_result_usd": str(stress_total),
        "beats_no_trade": beats_no_trade,
        "largest_loss_to_total_result_ratio": str(largest_loss_to_total_result_ratio),
        "largest_win_concentration": str(largest_win_concentration),
        "top2_win_concentration": str(top2_win_concentration),
        "episode_concentration_estimated": episode_concentration_estimated,
        "episode_largest_win_concentration": (
            str(episode_largest_win_concentration) if episode_concentration_estimated else None
        ),
        "episode_top2_win_concentration": (
            str(episode_top2_win_concentration) if episode_concentration_estimated else None
        ),
    }
    payload = {
        "schema_version": NO_TRADE_KILL_REPORT_SCHEMA_VERSION,
        "artifact_id": stable_hash(
            ["no-trade-kill-report", serialize_utc_z(created), summary, reason_codes]
        ),
        "created_at": serialize_utc_z(created),
        "producer": CryptoPerpProducer(command=NO_TRADE_KILL_REPORT_PRODUCER).model_dump(
            mode="json"
        ),
        "source_refs": list(source_refs),
        "boundary": CryptoPerpBoundary().model_dump(mode="json"),
        "input_artifacts": dict(input_artifacts),
        "event_count": event_count,
        "trade_event_count": executed_trade_count,
        "no_trade_win_count": no_trade_count,
        "trade_action_win_count": sum(1 for value in values if value > 0),
        "selected_action_counts": _selected_action_counts(signal_rows),
        "cost_adjusted_delta_vs_no_trade": str(total),
        "stress_delta_vs_no_trade": str(stress_total),
        "fee_drag": cost_breakdown["fee_drag"],
        "funding_drag": cost_breakdown["funding_drag"],
        "slippage_drag": cost_breakdown["slippage_drag"],
        "largest_win_concentration": str(largest_win_concentration),
        "top2_win_concentration": str(top2_win_concentration),
        "episode_concentration_estimated": episode_concentration_estimated,
        "episode_largest_win_concentration": (
            str(episode_largest_win_concentration) if episode_concentration_estimated else None
        ),
        "episode_top2_win_concentration": (
            str(episode_top2_win_concentration) if episode_concentration_estimated else None
        ),
        "largest_loss_concentration": str(largest_loss_concentration),
        "total_loss_usd": str(total_loss),
        "largest_loss_to_total_result_ratio": str(largest_loss_to_total_result_ratio),
        "kill_decision": kill_decision,
        "reason_codes": reason_codes,
        "upstream_gate_decision": upstream_gate_decision,
        "upstream_reason_codes": upstream_reason_codes,
        "upstream_blockers": upstream_blockers,
        "thresholds": {
            "min_events_for_review": MIN_EVENTS_FOR_REVIEW,
            "min_executed_trades_for_review": MIN_EXECUTED_TRADES_FOR_REVIEW,
            "max_largest_loss_to_total_result_ratio": str(MAX_LARGEST_LOSS_TO_TOTAL_RESULT_RATIO),
            "max_largest_win_concentration": str(MAX_LARGEST_WIN_CONCENTRATION),
            "max_top2_win_concentration": str(MAX_TOP2_WIN_CONCENTRATION),
            "max_episode_largest_win_concentration": str(MAX_LARGEST_WIN_CONCENTRATION),
            "max_episode_top2_win_concentration": str(MAX_TOP2_WIN_CONCENTRATION),
        },
        "summary": summary,
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


def write_no_trade_kill_report(
    *,
    signal_rows_path: Path,
    backtest_path: Path,
    stress_path: Path,
    gate_path: Path,
    out_dir: Path,
    created_at: datetime | str,
    tournament_rows_path: Path,
) -> NoTradeKillReportResult:
    signal_rows = _read_jsonl(signal_rows_path)
    backtest = _read_json(backtest_path)
    stress = _read_json(stress_path)
    gate = _validate_public_gate(_read_json(gate_path))
    tournament_rows = _validate_public_tournament_rows(_read_json(tournament_rows_path))
    refs = [
        _source_ref(signal_rows_path),
        _source_ref(backtest_path),
        _source_ref(stress_path),
        _source_ref(gate_path),
        _source_ref(tournament_rows_path),
    ]
    input_artifacts = {
        "signal_rows": signal_rows_path.as_posix(),
        "backtest": backtest_path.as_posix(),
        "stress": stress_path.as_posix(),
        "gate": gate_path.as_posix(),
        "tournament_rows": tournament_rows_path.as_posix(),
    }
    payload = build_no_trade_kill_report(
        signal_rows=signal_rows,
        backtest=backtest,
        stress=stress,
        gate=gate,
        tournament_rows=tournament_rows,
        created_at=created_at,
        input_artifacts=input_artifacts,
        source_refs=refs,
    )
    json_path = out_dir / "no_trade_kill_report.json"
    markdown_path = out_dir / "no_trade_kill_report.md"
    write_json_artifact(json_path, payload)
    write_text_artifact(markdown_path, _render_markdown(payload))
    return NoTradeKillReportResult(
        payload=payload, json_path=json_path, markdown_path=markdown_path
    )


def _render_markdown(payload: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# NO_TRADE Kill Report",
            "",
            f"- kill_decision: `{payload['kill_decision']}`",
            f"- upstream_gate_decision: `{payload['upstream_gate_decision']}`",
            f"- reason_codes: `{', '.join(cast(Sequence[str], payload['reason_codes']))}`",
            f"- event_count: `{payload['event_count']}`",
            f"- trade_event_count: `{payload['trade_event_count']}`",
            f"- cost_adjusted_delta_vs_no_trade: `{payload['cost_adjusted_delta_vs_no_trade']}`",
            f"- stress_delta_vs_no_trade: `{payload['stress_delta_vs_no_trade']}`",
            f"- largest_win_concentration: `{payload['largest_win_concentration']}`",
            f"- episode_largest_win_concentration: `{payload['episode_largest_win_concentration']}`",
            f"- episode_top2_win_concentration: `{payload['episode_top2_win_concentration']}`",
            f"- largest_loss_to_total_result_ratio: `{payload['largest_loss_to_total_result_ratio']}`",
            "- paper_permission_granted: `false`",
            "- permits_paper_order: `false`",
            "- actual_cash_used: `false`",
            "",
            "This artifact is a no-cash local simulation review aid. It does not grant Paper Observation permission, prove profit, or use actual cash.",
        ]
    )
