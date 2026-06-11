from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sis.research.ndx.artifacts import read_json, sha256_file, sha256_json, utc_now_iso, write_json
from sis.research.ndx.paper_observation_gate import APPROVE


@dataclass(frozen=True)
class OperatorPromotionResult:
    promotion_path: Path
    report_path: Path
    decision: str
    promotion_id: str


def run_operator_promotion(
    *,
    data_dir: Path,
    artifact_dir: Path,
    decision: Literal["promote_to_paper_observation", "hold", "reject"],
    reviewer: str | None,
    approval_reasons: list[str],
    rejection_reasons: list[str],
) -> OperatorPromotionResult:
    gate_path = artifact_dir / "paper_observation_gate_decision.json"
    if not gate_path.exists():
        raise FileNotFoundError(f"paper observation gate decision missing: {gate_path}")
    gate = read_json(gate_path)
    if gate.get("schema_version") != "ndx_paper_observation_gate_decision.v1":
        raise ValueError("paper observation gate schema_version mismatch.")
    _validate_gate_source_hashes(gate)
    if decision == "promote_to_paper_observation":
        if gate.get("decision") != APPROVE:
            raise ValueError(f"Layer 2.6 gate is not approved: {gate.get('decision')}")
        if gate.get("paper_observation_dry_run_ready") is not True:
            raise ValueError("Layer 2.6 gate did not prove paper observation dry-run readiness.")
        if not str(reviewer or "").strip():
            raise ValueError("reviewer is required for promote_to_paper_observation.")
        if not approval_reasons:
            raise ValueError("approval_reasons are required for promote_to_paper_observation.")
    else:
        if not rejection_reasons:
            raise ValueError("rejection_reasons are required for hold/reject.")

    stable_payload = {
        "schema_version": "ndx_operator_promotion_decision.v1",
        "decision": decision,
        "reviewer": reviewer,
        "approval_reasons": approval_reasons,
        "rejection_reasons": rejection_reasons,
        "source_paper_observation_gate_decision_id": gate["decision_id"],
        "source_paper_observation_gate_path": gate_path.as_posix(),
        "source_paper_observation_gate_hash": sha256_file(gate_path),
        "source_layer25_export_id": gate["source_layer25_export_id"],
        "source_layer25_export_manifest_path": gate["source_layer25_export_manifest_path"],
        "source_layer25_export_manifest_hash": gate["source_layer25_export_manifest_hash"],
        "strategy_signals_hash": gate["strategy_signals_hash"],
        "required_evidence": [
            "layer25_export",
            "paper_observation_gate",
            "manual_operator_review",
        ],
        "observed_evidence": (
            ["layer25_export", "paper_observation_gate", "manual_operator_review"]
            if decision == "promote_to_paper_observation"
            else ["paper_observation_gate"]
        ),
        "permits_paper_candidate": decision == "promote_to_paper_observation",
        "permits_paper_intent_preview": decision == "promote_to_paper_observation",
        "permits_paper_observation": decision == "promote_to_paper_observation",
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "external_api_used": False,
        "credentials_used": False,
        "wallet_used": False,
        "venue_write_used": False,
    }
    promotion_id = sha256_json(stable_payload)
    payload = {**stable_payload, "promotion_id": promotion_id, "created_at": utc_now_iso()}
    promotion_path = write_json(artifact_dir / "operator_promotion_decision.json", payload)
    report_path = _write_report(data_dir / "reports/ndx_operator_promotion_report.md", payload)
    return OperatorPromotionResult(
        promotion_path=promotion_path,
        report_path=report_path,
        decision=decision,
        promotion_id=promotion_id,
    )


def _validate_gate_source_hashes(gate: dict) -> None:
    for path_key, hash_key in (
        ("source_layer25_export_manifest_path", "source_layer25_export_manifest_hash"),
        ("strategy_signals_path", "strategy_signals_hash"),
        ("strategy_signal_manifest_path", "strategy_signal_manifest_hash"),
    ):
        path_value = str(gate.get(path_key) or "").strip()
        expected_hash = str(gate.get(hash_key) or "").strip()
        path = Path(path_value)
        if not path_value or not expected_hash:
            raise ValueError(f"paper observation gate missing {path_key}/{hash_key}.")
        if not path.exists():
            raise FileNotFoundError(f"paper observation gate source missing: {path}")
        if sha256_file(path) != expected_hash:
            raise ValueError(f"paper observation gate source hash mismatch: {path}")


def _write_report(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NDX Operator Promotion\n\n"
        f"- decision: {payload['decision']}\n"
        f"- permits_paper_observation: {str(payload['permits_paper_observation']).lower()}\n"
        "- permits_live_order: false\n"
        "- live_conversion_allowed: false\n",
        encoding="utf-8",
    )
    return path
