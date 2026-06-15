from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.reporting import write_markdown_report


@dataclass(frozen=True)
class BacktestConstraintBreakerDecisionResult:
    decision_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _decide(scorecard: dict[str, str], owner_approval_ref: str | None) -> tuple[str, list[str]]:
    failures: list[str] = []
    if scorecard["capability_gap"] not in {"material", "blocking"}:
        failures.append("capability_gap_not_material")
    if scorecard["expected_failure_mode_reduction"] != "high":
        failures.append("failure_mode_reduction_not_high")
    if scorecard["proof_fixture_status"] == "missing":
        failures.append("proof_fixture_missing")
    if scorecard["license_terms_status"] not in {"reviewed_allowed"} and not owner_approval_ref:
        failures.append("license_terms_not_approved")
    if scorecard["external_data_status"] == "uncontrolled_fetch":
        failures.append("external_data_uncontrolled")
    if scorecard["ci_cost_status"] != "acceptable":
        failures.append("ci_cost_not_acceptable")
    if scorecard["rollback_complexity"] not in {"low", "medium"}:
        failures.append("rollback_too_complex")
    if not failures:
        return "APPROVE_BREAK", ["scorecard_passed"]
    if "proof_fixture_missing" in failures or "license_terms_not_approved" in failures:
        return "NEEDS_MORE_EVIDENCE", failures
    return "REJECT_BREAK", failures


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Constraint Breaker Decision",
        "",
        f"- candidate_id: {payload['candidate_id']}",
        f"- decision: {payload['decision']}",
        f"- constraint_to_break: {payload['constraint_to_break']}",
        f"- reason_codes: {payload['reason_codes']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
    ]
    return write_markdown_report(path, lines)


def build_strategy_backtest_constraint_breaker_decision(
    *,
    candidate_id: str,
    constraint_to_break: str,
    capability_gap: str,
    expected_failure_mode_reduction: str,
    proof_fixture_status: str,
    license_terms_status: str,
    external_data_status: str,
    ci_cost_status: str,
    rollback_complexity: str,
    owner_approval_ref: str | None,
    out_dir: Path,
    reports_dir: Path,
    evidence_path: Path | None = None,
) -> BacktestConstraintBreakerDecisionResult:
    scorecard = {
        "capability_gap": capability_gap,
        "expected_failure_mode_reduction": expected_failure_mode_reduction,
        "proof_fixture_status": proof_fixture_status,
        "license_terms_status": license_terms_status,
        "external_data_status": external_data_status,
        "ci_cost_status": ci_cost_status,
        "rollback_complexity": rollback_complexity,
    }
    decision, reason_codes = _decide(scorecard, owner_approval_ref)
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_constraint_breaker_decision.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "candidate_id": candidate_id,
            "constraint_to_break": constraint_to_break,
            "capability_unlocked": candidate_id,
            "why_existing_lane_is_insufficient": "recorded_by_operator_input",
            "scorecard": scorecard,
            "owner_approval_ref": owner_approval_ref,
            "decision": decision,
            "reason_codes": reason_codes,
            "source_paths": {
                "evidence": evidence_path.as_posix() if evidence_path is not None else None
            },
            "source_hashes": {
                "evidence": _sha256_file(evidence_path)
                if evidence_path is not None and evidence_path.exists()
                else None
            },
            "measurement_plan": "run isolated artifact before optional dependency adoption",
            "rollback_plan": "keep runner optional and keep native result unchanged",
            "dependency_added": False,
            "engine_run": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    decision_path = out_dir / "strategy_backtest_constraint_breaker_decision.json"
    decision_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_constraint_breaker_decision_report.md", payload
    )
    return BacktestConstraintBreakerDecisionResult(
        decision_path=decision_path, report_path=report_path, payload=payload
    )
