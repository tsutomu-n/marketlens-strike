from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from sis.research.ndx.artifacts import read_json, sha256_file, sha256_json, utc_now_iso, write_json

PASS = "PASS_PAPER_OBSERVATION_REVIEW"
NEEDS_MORE = "NEEDS_MORE_PAPER_OBSERVATION"
STOP = "STOP_PAPER_OBSERVATION"
LEDGER_STATUSES = {"paper_filled", "blocked"}


@dataclass(frozen=True)
class PaperObservationReviewResult:
    decision_path: Path
    report_path: Path
    decision: str
    review_id: str


def run_paper_observation_review(
    *,
    data_dir: Path,
    artifact_dir: Path,
    reports_dir: Path,
    ledger_path: Path | None = None,
    min_fills_for_pass: int = 20,
    max_blocked_rate: float = 0.5,
    max_consecutive_blocked: int = 3,
    paper_notional_usd: float = 1000.0,
) -> PaperObservationReviewResult:
    if min_fills_for_pass < 1:
        raise ValueError("min_fills_for_pass must be >= 1")
    if not 0.0 <= max_blocked_rate <= 1.0:
        raise ValueError("max_blocked_rate must be between 0.0 and 1.0")
    if max_consecutive_blocked < 1:
        raise ValueError("max_consecutive_blocked must be >= 1")
    if paper_notional_usd <= 0:
        raise ValueError("paper_notional_usd must be positive")

    promotion_path = artifact_dir / "operator_promotion_decision.json"
    if not promotion_path.exists():
        raise FileNotFoundError(f"operator promotion decision missing: {promotion_path}")
    promotion = read_json(promotion_path)
    _validate_operator_promotion(promotion, promotion_path)

    selected_ledger_path = ledger_path or (data_dir / "paper/paper_observation_ledger.jsonl")
    entries = _read_ledger_entries(selected_ledger_path)
    artifact_hashes = _paper_artifact_hashes(data_dir)
    metrics = _ledger_metrics(entries)
    block_reasons = _review_block_reasons(
        metrics=metrics,
        paper_artifact_hashes=artifact_hashes,
        max_blocked_rate=max_blocked_rate,
        max_consecutive_blocked=max_consecutive_blocked,
    )
    if block_reasons:
        decision = STOP
    elif metrics["fills_count"] >= min_fills_for_pass:
        decision = PASS
    else:
        decision = NEEDS_MORE

    reason_codes: list[str] = []
    if decision == NEEDS_MORE:
        reason_codes.append("INSUFFICIENT_PAPER_FILLS")

    stable_payload = {
        "schema_version": "ndx_paper_observation_review_decision.v1",
        "decision": decision,
        "source_operator_promotion_decision_id": promotion["promotion_id"],
        "source_operator_promotion_path": promotion_path.as_posix(),
        "source_operator_promotion_hash": sha256_file(promotion_path),
        "source_paper_observation_gate_decision_id": promotion[
            "source_paper_observation_gate_decision_id"
        ],
        "paper_observation_ledger_path": selected_ledger_path.as_posix(),
        "paper_observation_ledger_hash": sha256_file(selected_ledger_path),
        "paper_artifacts": artifact_hashes,
        "paper_notional_usd": paper_notional_usd,
        "observation_thresholds": {
            "min_fills_for_pass": min_fills_for_pass,
            "max_blocked_rate": max_blocked_rate,
            "max_consecutive_blocked": max_consecutive_blocked,
        },
        "metrics": metrics,
        "reason_codes": reason_codes,
        "block_reasons": block_reasons,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "external_api_used": False,
        "credentials_used": False,
        "wallet_used": False,
        "venue_write_used": False,
    }
    review_id = sha256_json(stable_payload)
    payload = {**stable_payload, "review_id": review_id, "created_at": utc_now_iso()}
    decision_path = write_json(artifact_dir / "paper_observation_review_decision.json", payload)
    report_path = _write_report(
        reports_dir / "ndx_paper_observation_review_report.md", payload=payload
    )
    return PaperObservationReviewResult(
        decision_path=decision_path,
        report_path=report_path,
        decision=decision,
        review_id=review_id,
    )


def _validate_operator_promotion(promotion: dict[str, Any], promotion_path: Path) -> None:
    if promotion.get("schema_version") != "ndx_operator_promotion_decision.v1":
        raise ValueError("operator promotion schema_version mismatch.")
    if promotion.get("decision") != "promote_to_paper_observation":
        raise ValueError(f"operator promotion is not approved: {promotion.get('decision')}")
    if promotion.get("permits_paper_observation") is not True:
        raise ValueError("operator promotion does not permit paper observation.")
    for key in ("permits_live_order", "live_conversion_allowed", "wallet_used", "venue_write_used"):
        if promotion.get(key) is not False:
            raise ValueError(f"operator promotion must keep {key}=false.")
    gate_path = Path(str(promotion.get("source_paper_observation_gate_path") or ""))
    expected_hash = str(promotion.get("source_paper_observation_gate_hash") or "")
    if not gate_path.exists():
        raise FileNotFoundError(f"operator promotion source gate missing: {gate_path}")
    if sha256_file(gate_path) != expected_hash:
        raise ValueError("operator promotion source gate hash mismatch.")
    if not promotion_path.exists():
        raise FileNotFoundError(promotion_path)


def _read_ledger_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"paper observation ledger missing: {path}")
    entries: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError(f"paper observation ledger line {line_no} is not an object.")
        entries.append(value)
    if not entries:
        raise ValueError("paper observation ledger has no entries.")
    return entries


def _paper_artifact_hashes(data_dir: Path) -> dict[str, dict[str, str | bool]]:
    artifacts: dict[str, dict[str, str | bool]] = {}
    for name in ("orders", "fills", "positions"):
        path = data_dir / f"paper/{name}.parquet"
        artifacts[name] = {
            "path": path.as_posix(),
            "exists": path.exists(),
            "hash": sha256_file(path) if path.exists() else "",
        }
    return artifacts


def _ledger_metrics(entries: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(entry.get("status") or "") for entry in entries)
    block_reason_counts: Counter[str] = Counter()
    live_boundary_violations = 0
    unknown_statuses: list[str] = []
    consecutive_blocked = 0
    max_consecutive_blocked = 0
    for entry in entries:
        status = str(entry.get("status") or "")
        if status not in LEDGER_STATUSES and status not in unknown_statuses:
            unknown_statuses.append(status)
        if status == "blocked":
            consecutive_blocked += 1
            max_consecutive_blocked = max(max_consecutive_blocked, consecutive_blocked)
        else:
            consecutive_blocked = 0
        for reason in entry.get("block_reasons") or []:
            block_reason_counts[str(reason)] += 1
        if (
            entry.get("live_order_submitted") is not False
            or entry.get("wallet_used") is not False
            or entry.get("exchange_write_used") is not False
        ):
            live_boundary_violations += 1
    ledger_entry_count = len(entries)
    blocked_count = int(status_counts.get("blocked", 0))
    fills_count = int(status_counts.get("paper_filled", 0))
    return {
        "ledger_entry_count": ledger_entry_count,
        "fills_count": fills_count,
        "blocked_count": blocked_count,
        "blocked_rate": blocked_count / ledger_entry_count,
        "max_consecutive_blocked": max_consecutive_blocked,
        "status_counts": dict(status_counts),
        "block_reason_counts": dict(block_reason_counts),
        "live_boundary_violations": live_boundary_violations,
        "unknown_statuses": unknown_statuses,
    }


def _review_block_reasons(
    *,
    metrics: dict[str, Any],
    paper_artifact_hashes: dict[str, dict[str, str | bool]],
    max_blocked_rate: float,
    max_consecutive_blocked: int,
) -> list[str]:
    block_reasons: list[str] = []
    if metrics["live_boundary_violations"]:
        block_reasons.append("PAPER_BOUNDARY_VIOLATION")
    if metrics["unknown_statuses"]:
        block_reasons.append("UNKNOWN_LEDGER_STATUS")
    if metrics["blocked_rate"] > max_blocked_rate:
        block_reasons.append("BLOCKED_RATE_TOO_HIGH")
    if metrics["max_consecutive_blocked"] >= max_consecutive_blocked:
        block_reasons.append("CONSECUTIVE_BLOCKED_RUNS")
    missing = [name for name, artifact in paper_artifact_hashes.items() if not artifact["exists"]]
    if missing:
        block_reasons.append("PAPER_ARTIFACT_MISSING")
    return block_reasons


def _write_report(path: Path, *, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = payload["metrics"]
    path.write_text(
        "# NDX Paper Observation Review\n\n"
        f"- decision: {payload['decision']}\n"
        f"- fills_count: {metrics['fills_count']}\n"
        f"- blocked_count: {metrics['blocked_count']}\n"
        f"- blocked_rate: {metrics['blocked_rate']:.4f}\n"
        f"- max_consecutive_blocked: {metrics['max_consecutive_blocked']}\n"
        f"- block_reasons: {', '.join(payload['block_reasons']) or 'none'}\n"
        "- permits_live_order: false\n"
        "- live_conversion_allowed: false\n",
        encoding="utf-8",
    )
    return path
