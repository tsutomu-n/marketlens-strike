from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import polars as pl

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
    session_manifest_path: Path | None = None,
    min_fills_for_pass: int = 20,
    min_trading_days_for_pass: int = 10,
    max_blocked_rate: float = 0.5,
    max_consecutive_blocked: int = 3,
    max_open_position_age_hours: float = 0.0,
    paper_notional_usd: float = 1000.0,
) -> PaperObservationReviewResult:
    session_manifest = _read_session_manifest(
        session_manifest_path=session_manifest_path,
        explicit_ledger_path=ledger_path,
        promotion_path=artifact_dir / "operator_promotion_decision.json",
    )
    if session_manifest is not None:
        ledger_path = Path(str(session_manifest["observation_ledger_path"]))
        thresholds = session_manifest.get("thresholds")
        if isinstance(thresholds, dict):
            min_fills_for_pass = int(thresholds.get("min_fills_for_pass", min_fills_for_pass))
            min_trading_days_for_pass = int(
                thresholds.get("min_trading_days_for_pass", min_trading_days_for_pass)
            )
            max_blocked_rate = float(thresholds.get("max_blocked_rate", max_blocked_rate))
            max_consecutive_blocked = int(
                thresholds.get("max_consecutive_blocked", max_consecutive_blocked)
            )
            max_open_position_age_hours = float(
                thresholds.get(
                    "max_open_position_age_hours",
                    max_open_position_age_hours,
                )
            )

    if min_fills_for_pass < 1:
        raise ValueError("min_fills_for_pass must be >= 1")
    if min_trading_days_for_pass < 1:
        raise ValueError("min_trading_days_for_pass must be >= 1")
    if not 0.0 <= max_blocked_rate <= 1.0:
        raise ValueError("max_blocked_rate must be between 0.0 and 1.0")
    if max_consecutive_blocked < 1:
        raise ValueError("max_consecutive_blocked must be >= 1")
    if max_open_position_age_hours < 0:
        raise ValueError("max_open_position_age_hours must be >= 0")
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
    metrics.update(_paper_position_metrics(data_dir, max_open_position_age_hours))
    block_reasons = _review_block_reasons(
        metrics=metrics,
        paper_artifact_hashes=artifact_hashes,
        max_blocked_rate=max_blocked_rate,
        max_consecutive_blocked=max_consecutive_blocked,
    )
    if block_reasons:
        decision = STOP
    elif (
        metrics["fills_count"] >= min_fills_for_pass
        and metrics["trading_day_count"] >= min_trading_days_for_pass
        and metrics["timestamp_quality"] == "complete"
    ):
        decision = PASS
    else:
        decision = NEEDS_MORE

    reason_codes: list[str] = []
    if decision == NEEDS_MORE:
        if metrics["fills_count"] < min_fills_for_pass:
            reason_codes.append("INSUFFICIENT_PAPER_FILLS")
        if metrics["trading_day_count"] < min_trading_days_for_pass:
            reason_codes.append("INSUFFICIENT_TRADING_DAYS")
        if metrics["timestamp_quality"] != "complete":
            reason_codes.append("PAPER_OBSERVATION_TIMESTAMPS_INCOMPLETE")

    stable_payload = {
        "schema_version": "ndx_paper_observation_review_decision.v1",
        "decision": decision,
        "source_operator_promotion_decision_id": promotion["promotion_id"],
        "source_operator_promotion_path": promotion_path.as_posix(),
        "source_operator_promotion_hash": sha256_file(promotion_path),
        "source_paper_observation_gate_decision_id": promotion[
            "source_paper_observation_gate_decision_id"
        ],
        "source_paper_observation_session_manifest_path": (
            session_manifest_path.as_posix() if session_manifest_path else ""
        ),
        "source_paper_observation_session_manifest_hash": (
            sha256_file(session_manifest_path) if session_manifest_path else ""
        ),
        "paper_observation_ledger_path": selected_ledger_path.as_posix(),
        "paper_observation_ledger_hash": sha256_file(selected_ledger_path),
        "paper_artifacts": artifact_hashes,
        "paper_notional_usd": paper_notional_usd,
        "observation_thresholds": {
            "min_fills_for_pass": min_fills_for_pass,
            "min_trading_days_for_pass": min_trading_days_for_pass,
            "max_blocked_rate": max_blocked_rate,
            "max_consecutive_blocked": max_consecutive_blocked,
            "max_open_position_age_hours": max_open_position_age_hours,
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
        "exchange_write_used": False,
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


def _read_session_manifest(
    *,
    session_manifest_path: Path | None,
    explicit_ledger_path: Path | None,
    promotion_path: Path,
) -> dict[str, Any] | None:
    if session_manifest_path is None:
        return None
    if not session_manifest_path.exists():
        raise FileNotFoundError(
            f"paper observation session manifest missing: {session_manifest_path}"
        )
    manifest = read_json(session_manifest_path)
    if manifest.get("schema_version") != "paper_observation_session_manifest.v1":
        raise ValueError("paper observation session manifest schema_version mismatch.")
    raw_ledger_path = manifest.get("observation_ledger_path")
    if not isinstance(raw_ledger_path, str) or not raw_ledger_path.strip():
        raise ValueError("paper observation session manifest missing observation_ledger_path.")
    manifest_ledger_path = Path(raw_ledger_path)
    if explicit_ledger_path is not None and not _same_path(
        explicit_ledger_path, manifest_ledger_path
    ):
        raise ValueError("paper observation session manifest ledger path mismatch.")
    _validate_manifest_source_hash(
        manifest,
        path_key="source_backtest_acceptance_path",
        hash_key="source_backtest_acceptance_sha256",
        label="backtest acceptance",
    )
    raw_promotion_path = manifest.get("source_operator_promotion_path")
    if not isinstance(raw_promotion_path, str) or not raw_promotion_path.strip():
        raise ValueError("paper observation session manifest missing operator promotion path.")
    manifest_promotion_path = Path(raw_promotion_path)
    if not _same_path(manifest_promotion_path, promotion_path):
        raise ValueError("paper observation session manifest operator promotion path mismatch.")
    _validate_manifest_source_hash(
        manifest,
        path_key="source_operator_promotion_path",
        hash_key="source_operator_promotion_sha256",
        label="operator promotion",
    )
    _validate_manifest_source_hash(
        manifest,
        path_key="source_intent_preview_path",
        hash_key="source_intent_preview_sha256",
        label="intent preview",
    )
    return manifest


def _validate_manifest_source_hash(
    manifest: dict[str, Any],
    *,
    path_key: str,
    hash_key: str,
    label: str,
) -> None:
    raw_path = manifest.get(path_key)
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"paper observation session manifest missing {label} path.")
    source_path = Path(raw_path)
    if not source_path.exists():
        raise FileNotFoundError(f"paper observation session source {label} missing: {source_path}")
    expected_hash = str(manifest.get(hash_key) or "")
    if sha256_file(source_path) != expected_hash:
        raise ValueError(f"paper observation session {label} hash mismatch.")


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


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
    trading_days: set[str] = set()
    missing_timestamps = 0
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
        if any(
            key in entry and entry.get(key) is not False
            for key in (
                "live_order_submitted",
                "wallet_used",
                "exchange_write_used",
                "venue_write_used",
            )
        ):
            live_boundary_violations += 1
        timestamp = _entry_timestamp(entry)
        if timestamp is None:
            missing_timestamps += 1
        else:
            trading_days.add(timestamp.date().isoformat())
    ledger_entry_count = len(entries)
    blocked_count = int(status_counts.get("blocked", 0))
    fills_count = int(status_counts.get("paper_filled", 0))
    timestamp_quality = "complete" if missing_timestamps == 0 else "missing_or_partial"
    return {
        "ledger_entry_count": ledger_entry_count,
        "fills_count": fills_count,
        "blocked_count": blocked_count,
        "blocked_rate": blocked_count / ledger_entry_count,
        "max_consecutive_blocked": max_consecutive_blocked,
        "trading_day_count": len(trading_days),
        "trading_days": sorted(trading_days),
        "missing_timestamp_count": missing_timestamps,
        "timestamp_quality": timestamp_quality,
        "status_counts": dict(status_counts),
        "block_reason_counts": dict(block_reason_counts),
        "live_boundary_violations": live_boundary_violations,
        "unknown_statuses": unknown_statuses,
    }


def _entry_timestamp(entry: dict[str, Any]) -> datetime | None:
    for key in ("created_at", "ts_fill", "fill_ts", "ts_order", "order_ts", "quote_ts"):
        value = entry.get(key)
        if value is None:
            continue
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            continue
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _paper_position_metrics(
    data_dir: Path,
    max_open_position_age_hours: float,
) -> dict[str, Any]:
    positions_path = data_dir / "paper/positions.parquet"
    if not positions_path.exists():
        return {
            "open_position_count": 0,
            "max_open_position_age_hours": None,
            "open_position_age_threshold_hours": max_open_position_age_hours,
        }
    positions = pl.read_parquet(positions_path)
    if positions.is_empty() or "opened_at" not in positions.columns:
        return {
            "open_position_count": positions.height,
            "max_open_position_age_hours": None,
            "open_position_age_threshold_hours": max_open_position_age_hours,
        }
    now = datetime.now(timezone.utc)
    max_age: float | None = None
    for value in positions.get_column("opened_at").to_list():
        if value is None:
            continue
        opened_at = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        age_hours = (now - opened_at).total_seconds() / 3600
        max_age = age_hours if max_age is None else max(max_age, age_hours)
    return {
        "open_position_count": positions.height,
        "max_open_position_age_hours": max_age,
        "open_position_age_threshold_hours": max_open_position_age_hours,
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
    threshold = metrics.get("open_position_age_threshold_hours")
    max_age = metrics.get("max_open_position_age_hours")
    if threshold and max_age is not None and max_age > threshold:
        block_reasons.append("OPEN_POSITION_TOO_OLD")
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
