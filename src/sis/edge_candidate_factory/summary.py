from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.strategy_inputs.io import read_mapping_file


def _read_payload(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        return read_mapping_file(path)
    except Exception:
        return None


def _artifact_state(path: Path | None) -> dict[str, Any]:
    payload = _read_payload(path)
    return {
        "path": path.as_posix() if path is not None else None,
        "exists": bool(path is not None and path.exists()),
        "schema_version": payload.get("schema_version") if payload else None,
    }


def _artifact_states(paths: list[Path] | None) -> list[dict[str, Any]]:
    return [_artifact_state(path) for path in (paths or [])]


def _known_gaps(payload: dict[str, Any] | None) -> list[str]:
    if payload is None:
        return []
    value = payload.get("known_gaps")
    return [str(item) for item in value] if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def build_edge_candidate_artifact_summary(
    *,
    candidate_report_path: Path | None = None,
    backtest_kill_gate_paths: list[Path] | None = None,
    virtual_execution_gate_paths: list[Path] | None = None,
    risk_actual_cash_handoff_paths: list[Path] | None = None,
    adversarial_review_paths: list[Path] | None = None,
) -> dict[str, Any]:
    candidate_report = _read_payload(candidate_report_path)
    backtest_payloads = [
        payload
        for path in (backtest_kill_gate_paths or [])
        if (payload := _read_payload(path)) is not None
    ]
    virtual_payloads = [
        payload
        for path in (virtual_execution_gate_paths or [])
        if (payload := _read_payload(path)) is not None
    ]
    handoff_payloads = [
        payload
        for path in (risk_actual_cash_handoff_paths or [])
        if (payload := _read_payload(path)) is not None
    ]
    adversarial_payloads = [
        payload
        for path in (adversarial_review_paths or [])
        if (payload := _read_payload(path)) is not None
    ]

    candidate_count_total = (
        int(candidate_report.get("candidate_count_total", 0)) if candidate_report else None
    )
    candidate_count_rejected = (
        int(candidate_report.get("candidate_count_rejected", 0)) if candidate_report else None
    )
    virtual_passed_count = sum(
        1
        for payload in virtual_payloads
        if payload.get("gate_status") == "VIRTUAL_PASSED_EXECUTION_LIFECYCLE"
    )
    actual_cash_ready_count = sum(
        1
        for payload in handoff_payloads
        if payload.get("actual_cash_report_gate_input_status") == "READY_WITH_ACTUAL_CASH_ROWS"
    )

    blockers: list[str] = []
    if candidate_report_path is not None and not candidate_report_path.exists():
        blockers.append("candidate report missing")
    for label, paths in (
        ("backtest kill gate missing", backtest_kill_gate_paths or []),
        ("virtual execution gate missing", virtual_execution_gate_paths or []),
        ("risk actual cash handoff missing", risk_actual_cash_handoff_paths or []),
    ):
        blockers.extend(label for path in paths if not path.exists())
    for payload in [candidate_report, *backtest_payloads, *virtual_payloads, *handoff_payloads]:
        blockers.extend(_known_gaps(payload))
    for payload in backtest_payloads:
        if payload.get("gate_status") == "KILL":
            blockers.append("backtest kill gate killed candidate")
    for payload in virtual_payloads:
        status = payload.get("gate_status")
        if isinstance(status, str) and status.startswith("VIRTUAL_FAILED"):
            blockers.append(status.lower())
    for payload in handoff_payloads:
        if payload.get("actual_cash_report_gate_input_status") == "BLOCKED_NEEDS_ACTUAL_CASH_ROWS":
            blockers.append("actual cash rows are missing")
    blockers = _unique(blockers)

    if candidate_report is None:
        core_status = "MISSING_CORE_ARTIFACTS"
        next_action = "run edge-candidate-factory-build"
    elif actual_cash_ready_count:
        core_status = "ACTUAL_CASH_READY_FOR_MANUAL_REVIEW"
        next_action = "run manual risk review before actual cash report gate"
    elif virtual_passed_count:
        core_status = "VIRTUAL_PASSED_NEEDS_ACTUAL_CASH_ROWS"
        next_action = "collect actual cash rows"
    elif any(payload.get("gate_status") == "KILL" for payload in backtest_payloads):
        core_status = "CANDIDATE_KILLED"
        next_action = "review killed candidates or generate new candidates"
    elif not backtest_payloads:
        core_status = "NEEDS_BACKTEST_KILL_GATE"
        next_action = "run edge-candidate-backtest-kill-gate"
    elif not virtual_payloads:
        core_status = "NEEDS_VIRTUAL_EXECUTION_GATE"
        next_action = "run edge-candidate-virtual-execution-gate"
    else:
        core_status = "RESEARCH_ONLY"
        next_action = "manual review required"

    return {
        "summary_kind": "edge_candidate_artifact_summary.v1",
        "core_status": core_status,
        "next_action": next_action,
        "candidate_count_total": candidate_count_total,
        "candidate_count_rejected": candidate_count_rejected,
        "shortlist_for_virtual_count": 0,
        "virtual_passed_count": virtual_passed_count,
        "actual_cash_ready_count": actual_cash_ready_count,
        "known_gap_count": len(blockers),
        "top_blocker_reasons": blockers[:5],
        "production_exchange_write_used": False,
        "live_order_allowed": False,
        "artifacts": {
            "candidate_report": _artifact_state(candidate_report_path),
            "backtest_kill_gates": _artifact_states(backtest_kill_gate_paths),
            "virtual_execution_gates": _artifact_states(virtual_execution_gate_paths),
            "risk_actual_cash_handoffs": _artifact_states(risk_actual_cash_handoff_paths),
            "adversarial_reviews": _artifact_states(adversarial_review_paths),
        },
        "addon_status": {
            "adversarial_review_statuses": [
                str(payload.get("review_status"))
                for payload in adversarial_payloads
                if payload.get("review_status") is not None
            ]
        },
    }
