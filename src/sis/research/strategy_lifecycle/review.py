from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sis.research.ndx.artifacts import read_json, sha256_file, sha256_json, utc_now_iso, write_json

REJECT_OR_REVISE = "REJECT_OR_REVISE"
CONTINUE_RESEARCH = "CONTINUE_RESEARCH"
BACKTEST_ACCEPTED = "BACKTEST_ACCEPTED"
CONTINUE_PAPER_OBSERVATION = "CONTINUE_PAPER_OBSERVATION"
CONTINUE_EXECUTION_READINESS = "CONTINUE_EXECUTION_READINESS"
ELIGIBLE_FOR_LIVE_CANARY_PLAN = "ELIGIBLE_FOR_LIVE_CANARY_PLAN"
BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"

BOUNDARY_KEYS = {
    "permits_live_order",
    "live_conversion_allowed",
    "live_order_submitted",
    "wallet_used",
    "venue_write_used",
    "exchange_write_used",
    "credentials_used",
    "external_api_used",
}


@dataclass(frozen=True)
class StrategyLifecycleReviewResult:
    decision_path: Path
    report_path: Path
    decision: str
    review_id: str


def run_strategy_lifecycle_review(
    *,
    data_dir: Path,
    out_dir: Path,
    reports_dir: Path,
    backtest_decision_path: Path | None = None,
    paper_review_path: Path | None = None,
    phase_gate_path: Path | None = None,
) -> StrategyLifecycleReviewResult:
    selected_backtest_path = backtest_decision_path or (
        data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json"
    )
    selected_paper_path = paper_review_path or (
        data_dir / "research/ndx/paper_observation_review_decision.json"
    )
    selected_phase_gate_path = phase_gate_path or (data_dir / "ops/phase_gate_review_summary.json")

    backtest = _read_optional(selected_backtest_path)
    paper = _read_optional(selected_paper_path)
    phase_gate = _read_optional(selected_phase_gate_path)
    boundary_flags = _boundary_flags(backtest, paper, phase_gate)
    blocker_counts = _blocker_counts(phase_gate)

    decision, reasons, next_actions = _decide(
        backtest=backtest,
        paper=paper,
        phase_gate=phase_gate,
        boundary_flags=boundary_flags,
        blocker_counts=blocker_counts,
    )
    stable_payload = {
        "schema_version": "strategy_lifecycle_review.v1",
        "decision": decision,
        "decision_reasons": reasons,
        "next_actions": next_actions,
        "source_backtest_acceptance_path": selected_backtest_path.as_posix(),
        "source_backtest_acceptance_hash": _hash_if_exists(selected_backtest_path),
        "source_paper_review_path": selected_paper_path.as_posix(),
        "source_paper_review_hash": _hash_if_exists(selected_paper_path),
        "source_phase_gate_path": selected_phase_gate_path.as_posix(),
        "source_phase_gate_hash": _hash_if_exists(selected_phase_gate_path),
        "input_status": {
            "backtest_acceptance_present": backtest is not None,
            "paper_review_present": paper is not None,
            "phase_gate_present": phase_gate is not None,
        },
        "blocker_counts": blocker_counts,
        "boundary_flags": boundary_flags,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    review_id = sha256_json(stable_payload)
    payload = {**stable_payload, "review_id": review_id, "created_at": utc_now_iso()}
    decision_path = write_json(out_dir / "strategy_lifecycle_review.json", payload)
    report_path = _write_report(reports_dir / "strategy_lifecycle_review.md", payload)
    return StrategyLifecycleReviewResult(
        decision_path=decision_path,
        report_path=report_path,
        decision=decision,
        review_id=review_id,
    )


def _read_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json(path)


def _hash_if_exists(path: Path) -> str:
    return sha256_file(path) if path.exists() else ""


def _boundary_flags(*payloads: dict[str, Any] | None) -> dict[str, bool]:
    flags: dict[str, bool] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in BOUNDARY_KEYS and child is not False:
                    flags[key] = True
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for payload in payloads:
        visit(payload)
    return flags


def _blocker_counts(phase_gate: dict[str, Any] | None) -> dict[str, int]:
    counts = {
        "P2_BLOCKER": 0,
        "LIVE_READINESS_BLOCKER": 0,
    }
    if not isinstance(phase_gate, dict):
        return counts
    raw_counts = phase_gate.get("execution_drift_classification_counts")
    if isinstance(raw_counts, dict):
        for key in counts:
            value = raw_counts.get(key)
            if isinstance(value, int):
                counts[key] = value
    for blocker in phase_gate.get("blockers") or []:
        text = str(blocker)
        if "P2_BLOCKER" in text:
            counts["P2_BLOCKER"] += 1
        if "LIVE_READINESS_BLOCKER" in text:
            counts["LIVE_READINESS_BLOCKER"] += 1
    return counts


def _decide(
    *,
    backtest: dict[str, Any] | None,
    paper: dict[str, Any] | None,
    phase_gate: dict[str, Any] | None,
    boundary_flags: dict[str, bool],
    blocker_counts: dict[str, int],
) -> tuple[str, list[str], list[str]]:
    if boundary_flags:
        return (
            BLOCKED_BOUNDARY_VIOLATION,
            ["BOUNDARY_FLAG_PRESENT"],
            ["Investigate and remove prohibited live, wallet, credential, or write side effect."],
        )
    if backtest is None:
        return (
            CONTINUE_RESEARCH,
            ["BACKTEST_ACCEPTANCE_MISSING"],
            ["Run strategy-author-run --through backtest and strategy-backtest-acceptance."],
        )
    backtest_decision = str(backtest.get("decision") or "")
    if backtest_decision == "NEEDS_BACKTEST":
        return (
            CONTINUE_RESEARCH,
            ["BACKTEST_REQUIRED"],
            ["Generate strategy backtest metrics and rerun backtest acceptance."],
        )
    if backtest_decision == "FAIL_BACKTEST_ACCEPTANCE":
        return (
            REJECT_OR_REVISE,
            ["BACKTEST_ACCEPTANCE_FAILED"],
            ["Revise strategy before paper observation."],
        )
    if backtest_decision == "BLOCK_BACKTEST_BOUNDARY":
        return (
            BLOCKED_BOUNDARY_VIOLATION,
            ["BACKTEST_BOUNDARY_BLOCK"],
            ["Fix boundary violation in backtest artifact."],
        )
    if backtest_decision != "PASS_BACKTEST_ACCEPTANCE":
        return (
            CONTINUE_RESEARCH,
            ["BACKTEST_ACCEPTANCE_UNKNOWN"],
            ["Regenerate backtest acceptance artifact."],
        )
    if paper is None:
        return (
            BACKTEST_ACCEPTED,
            ["PAPER_OBSERVATION_REVIEW_MISSING"],
            ["Run paper observation and paper observation review."],
        )
    paper_decision = str(paper.get("decision") or "")
    paper_block_reasons = [str(reason) for reason in paper.get("block_reasons") or []]
    if paper_decision == "STOP_PAPER_OBSERVATION":
        if any("BOUNDARY" in reason for reason in paper_block_reasons):
            return (
                BLOCKED_BOUNDARY_VIOLATION,
                ["PAPER_BOUNDARY_BLOCK"],
                ["Investigate paper boundary violation."],
            )
        return (
            REJECT_OR_REVISE,
            ["PAPER_OBSERVATION_STOPPED"],
            ["Revise or reject strategy before further paper observation."],
        )
    if paper_decision == "NEEDS_MORE_PAPER_OBSERVATION":
        return (
            CONTINUE_PAPER_OBSERVATION,
            ["PAPER_OBSERVATION_INSUFFICIENT"],
            ["Continue paper observation until thresholds are met."],
        )
    if paper_decision != "PASS_PAPER_OBSERVATION_REVIEW":
        return (
            CONTINUE_PAPER_OBSERVATION,
            ["PAPER_OBSERVATION_UNKNOWN"],
            ["Regenerate paper observation review artifact."],
        )
    if phase_gate is None:
        return (
            CONTINUE_EXECUTION_READINESS,
            ["PHASE_GATE_MISSING"],
            ["Run phase-gate-review."],
        )
    if blocker_counts.get("P2_BLOCKER", 0) > 0:
        return (
            CONTINUE_EXECUTION_READINESS,
            ["P2_BLOCKERS_REMAIN"],
            ["Resolve phase gate P2 blockers."],
        )
    if blocker_counts.get("LIVE_READINESS_BLOCKER", 0) > 0:
        return (
            CONTINUE_EXECUTION_READINESS,
            ["LIVE_READINESS_BLOCKERS_REMAIN"],
            ["Resolve live-readiness blockers in a separate plan."],
        )
    phase_decision = str(phase_gate.get("decision") or "")
    if phase_decision not in {"READ_ONLY_GO", "PAPER_GO"}:
        return (
            CONTINUE_EXECUTION_READINESS,
            ["PHASE_GATE_NOT_GO"],
            ["Review phase-gate decision before live canary planning."],
        )
    return (
        ELIGIBLE_FOR_LIVE_CANARY_PLAN,
        ["BACKTEST_PAPER_AND_GATE_THRESHOLDS_MET"],
        ["Write a separate live canary implementation plan before any live order work."],
    )


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Strategy Lifecycle Review",
        "",
        f"- decision: {payload['decision']}",
        f"- review_id: {payload['review_id']}",
        f"- decision_reasons: {', '.join(payload['decision_reasons']) or 'none'}",
        "- permits_live_order: false",
        "",
        "This review does not permit live orders. A separate live canary plan is required before any live execution work.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
