from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from sis.research.ndx.artifacts import read_json, sha256_file, sha256_json, utc_now_iso, write_json

APPROVE = "APPROVE_PAPER_OBSERVATION_REVIEW"
REVISE = "REVISE_2_5"
REJECT = "REJECT_PAPER_OBSERVATION_GATE"


@dataclass(frozen=True)
class PaperObservationGateResult:
    decision_path: Path
    report_path: Path
    decision: str
    decision_id: str


def run_paper_observation_gate(
    *,
    data_dir: Path,
    artifact_dir: Path,
    reports_dir: Path,
    quotes_path: Path,
    min_era_count: int = 3,
    min_signal_count: int = 30,
    max_tested_variant_count: int = 1,
    fixture_evidence_policy: str = "warn",
) -> PaperObservationGateResult:
    if fixture_evidence_policy not in {"warn", "reject"}:
        raise ValueError("fixture_evidence_policy must be one of: warn, reject")
    export_path = artifact_dir / "strategy_lab_research_export_manifest.json"
    signals_path = data_dir / "research/strategy_signals.parquet"
    signal_manifest_path = data_dir / "research/strategy_signal_manifest.json"
    for path in (export_path, signals_path, signal_manifest_path, quotes_path):
        if not path.exists():
            raise FileNotFoundError(f"required Layer 2.6 input missing: {path}")

    export = read_json(export_path)
    _validate_export(export, export_path, signals_path, signal_manifest_path)
    signals = pl.read_parquet(signals_path)
    quotes = pl.read_parquet(quotes_path)
    signal_count = signals.height
    era_count = _era_count(signals)
    quote_info = _quote_info(quotes)
    tested_variant_count = int(export.get("tested_variant_count") or 0)
    evidence_tier = "paper_observation_dry_run" if quote_info["available"] else "historical_local"
    sample_scope = "local_runtime_artifact"

    block_reasons: list[str] = []
    reason_codes: list[str] = []
    if signal_count < min_signal_count:
        block_reasons.append("INSUFFICIENT_SIGNAL_COUNT")
    if era_count < min_era_count:
        block_reasons.append("INSUFFICIENT_ERA_COUNT")
    if tested_variant_count > max_tested_variant_count:
        block_reasons.append("TOO_MANY_TESTED_VARIANTS")
    if not quote_info["available"]:
        block_reasons.append("PAPER_QUOTE_MISSING")
    if evidence_tier == "historical_local":
        reason_codes.append("LOCAL_HISTORICAL_EVIDENCE_ONLY")
    if fixture_evidence_policy == "reject" and evidence_tier == "historical_local":
        block_reasons.append("FIXTURE_OR_HISTORICAL_EVIDENCE_REJECTED")

    decision = APPROVE if not block_reasons else REVISE
    stable_payload = {
        "schema_version": "ndx_paper_observation_gate_decision.v1",
        "source_layer25_export_id": export["export_id"],
        "source_layer25_export_manifest_path": export_path.as_posix(),
        "source_layer25_export_manifest_hash": sha256_file(export_path),
        "strategy_signals_path": signals_path.as_posix(),
        "strategy_signals_hash": sha256_file(signals_path),
        "strategy_signal_manifest_path": signal_manifest_path.as_posix(),
        "strategy_signal_manifest_hash": sha256_file(signal_manifest_path),
        "signal_count": signal_count,
        "era_count": era_count,
        "sample_scope": sample_scope,
        "evidence_tier": evidence_tier,
        "quotes_path": quotes_path.as_posix(),
        "quotes_hash": sha256_file(quotes_path),
        "paper_quote_available": quote_info["available"],
        "paper_quote_latest_ts": quote_info["latest_ts"],
        "paper_observation_dry_run_ready": bool(quote_info["available"] and not block_reasons),
        "split_method": "local_signal_era_summary",
        "tested_variant_count": tested_variant_count,
        "acceptance_thresholds": {
            "min_era_count": min_era_count,
            "min_signal_count": min_signal_count,
            "max_tested_variant_count": max_tested_variant_count,
            "fixture_evidence_policy": fixture_evidence_policy,
        },
        "metrics": {
            "signal_count": signal_count,
            "era_count": era_count,
            "paper_quote_available": quote_info["available"],
        },
        "decision": decision,
        "reason_codes": reason_codes,
        "block_reasons": block_reasons,
        "permits_operator_promotion_review": decision == APPROVE,
        "permits_paper_observation_review": decision == APPROVE,
        "permits_paper_candidate": False,
        "permits_paper_intent_preview": False,
        "permits_live_order": False,
        "external_api_used": False,
        "credentials_used": False,
        "wallet_used": False,
        "venue_write_used": False,
    }
    decision_id = sha256_json(stable_payload)
    payload = {**stable_payload, "decision_id": decision_id, "created_at": utc_now_iso()}
    decision_path = write_json(artifact_dir / "paper_observation_gate_decision.json", payload)
    report_path = _write_report(
        reports_dir / "ndx_paper_observation_gate_report.md", payload=payload
    )
    return PaperObservationGateResult(
        decision_path=decision_path,
        report_path=report_path,
        decision=decision,
        decision_id=decision_id,
    )


def _validate_export(
    export: dict[str, Any], export_path: Path, signals_path: Path, signal_manifest_path: Path
) -> None:
    if export.get("schema_version") != "ndx_strategy_lab_research_export_manifest.v1":
        raise ValueError("Layer 2.5 export schema_version mismatch.")
    if export.get("research_only") is not True:
        raise ValueError("Layer 2.5 export must be research_only.")
    for key in (
        "permits_backtest",
        "permits_paper_candidate",
        "permits_paper_intent_preview",
        "permits_live_order",
    ):
        if export.get(key) is not False:
            raise ValueError(f"Layer 2.5 export must keep {key}=false.")
    if sha256_file(signals_path) != export.get("strategy_signals_hash"):
        raise ValueError("strategy_signals_hash mismatch.")
    if sha256_file(signal_manifest_path) != export.get("strategy_signal_manifest_hash"):
        raise ValueError("strategy_signal_manifest_hash mismatch.")
    if not export_path.exists():
        raise FileNotFoundError(export_path)


def _era_count(signals: pl.DataFrame) -> int:
    if "ts_signal" not in signals.columns or signals.is_empty():
        return 0
    eras = {
        value.strftime("%Y-%m") if isinstance(value, datetime) else str(value)[:7]
        for value in signals.get_column("ts_signal").drop_nulls().to_list()
    }
    return len(eras)


def _quote_info(quotes: pl.DataFrame) -> dict[str, Any]:
    required = {"venue", "canonical_symbol", "ts_client"}
    if not required.issubset(set(quotes.columns)):
        return {"available": False, "latest_ts": None}
    filtered = quotes.filter(
        (pl.col("venue") == "trade_xyz")
        & (pl.col("canonical_symbol").str.to_uppercase() == "XYZ100")
    )
    if filtered.is_empty():
        return {"available": False, "latest_ts": None}
    latest = filtered.sort("ts_client").tail(1).to_dicts()[0]
    tradable = bool(latest.get("is_tradable", True))
    latest_ts = latest["ts_client"]
    latest_ts_text = latest_ts.isoformat() if isinstance(latest_ts, datetime) else str(latest_ts)
    return {"available": tradable, "latest_ts": latest_ts_text}


def _write_report(path: Path, *, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NDX Paper Observation Gate\n\n"
        f"- decision: {payload['decision']}\n"
        f"- signal_count: {payload['signal_count']}\n"
        f"- era_count: {payload['era_count']}\n"
        f"- evidence_tier: {payload['evidence_tier']}\n"
        f"- paper_observation_dry_run_ready: {str(payload['paper_observation_dry_run_ready']).lower()}\n"
        "- alpha_proof: false\n"
        "- live_ready: false\n",
        encoding="utf-8",
    )
    return path
