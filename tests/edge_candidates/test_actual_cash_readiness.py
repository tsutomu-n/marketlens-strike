from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.edge_candidates.actual_cash_readiness import (
    ActualCashReadinessPacketError,
    ProfitCoreActualCashReadinessStatus,
    build_and_write_actual_cash_readiness_packet,
    build_actual_cash_readiness_packet,
)
from sis.strategy_inputs.io import write_json_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64
runner = CliRunner()


def _write_evidence_packet(tmp_path: Path) -> Path:
    path = tmp_path / "profit_core_evidence_packet.json"
    write_json_artifact(path, _evidence_packet_payload())
    return path


def _write_adversarial_review(tmp_path: Path, *, hard_blocker_count: int = 0) -> Path:
    path = tmp_path / "profit_core_adversarial_review.json"
    status = "NO_ADDITIONAL_BLOCKER_FOUND"
    findings = []
    if hard_blocker_count:
        status = "OVERCLAIM_FLAG"
        findings = [
            {
                "finding_id": "machine-actual-cash-overclaim",
                "status": "OVERCLAIM_FLAG",
                "severity": "BLOCKER",
                "message": "Actual-cash overclaim blocks readiness.",
                "source": "MACHINE_CLAIM_DIFF",
                "evidence_refs": [{"ref_type": "claim_finding", "ref_id": "claim-actual-cash"}],
                "machine_checkable": True,
                "hard_blocker": True,
            }
        ]
    write_json_artifact(
        path,
        {
            "schema_version": "profit_core_adversarial_review.v1",
            "review_id": "idea-cand-001-profit-core-adversarial-review",
            "recorded_at": "2026-07-01T07:00:00Z",
            "producer": {"tool": "sis", "command": "edge-candidate-adversarial-review-record"},
            "candidate_id": "idea-cand-001",
            "evidence_packet_ref": {
                "ref_type": "evidence_packet",
                "ref_id": "idea-cand-001-profit-core-evidence-packet",
                "path": "profit_core_evidence_packet.json",
                "sha256": SHA256_A,
            },
            "review_status": status,
            "findings": findings,
            "machine_finding_count": hard_blocker_count,
            "manual_finding_count": 0,
            "hard_blocker_count": hard_blocker_count,
            "review_mode": "local_manual_import",
            "redaction_policy": "LOCAL_ONLY_NO_EXTERNAL_SEND",
            "llm_api_used": False,
            "external_send_performed": False,
            "approval_allowed": False,
            "permission_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "tiny_live_allowed": False,
            "no_additional_blocker_is_approval": False,
            "boundary": {
                "actual_cash_decision_allowed": False,
                "permits_live_order": False,
                "permits_paper_order": False,
                "permits_tiny_live": False,
                "permits_actual_cash": False,
                "production_exchange_write_used": False,
                "live_order_submitted": False,
                "wallet_used": False,
                "signing_used": False,
                "llm_api_used": False,
                "external_send_performed": False,
                "gate_override_allowed": False,
                "strategy_rewrite_allowed": False,
                "pnl_metric_authority": False,
            },
        },
    )
    return path


def _write_readiness_plan(tmp_path: Path, *, missing_controls: bool = False) -> Path:
    path = tmp_path / "actual_cash_readiness_plan.json"
    payload = _readiness_plan_payload()
    if missing_controls:
        payload["operational_controls"]["stop_conditions"] = []
    write_json_artifact(path, payload)
    return path


def _write_risk_sprint_isolation(tmp_path: Path) -> Path:
    path = tmp_path / "profit_core_risk_taker_sprint_isolation.json"
    write_json_artifact(
        path,
        {
            "schema_version": "profit_core_risk_taker_sprint_isolation.v1",
            "isolation_id": "risk-sprint-001-risk-taker-sprint-isolation",
            "recorded_at": "2026-07-01T07:10:00Z",
            "producer": {
                "tool": "sis",
                "command": "edge-candidate-risk-taker-sprint-isolation-record",
            },
            "protocol_id": "risk-sprint-001",
            "candidate_set_id": "ndx-candidate-set-001",
            "multiplicity_account_id": "risk-sprint-001-trial-multiplicity",
            "mode": "risk_taker_sprint",
            "output_label": "SPECULATIVE_SPRINT",
            "sealed_holdout_window_id": "sprint-holdout-2026-q3",
            "protocol_ref": _artifact_ref("risk_taker_sprint_protocol"),
            "candidate_set_ref": _artifact_ref("risk_taker_sprint_candidate_set"),
            "search_ledger_ref": _artifact_ref("risk_taker_sprint_search_ledger"),
            "multiplicity_account_ref": _artifact_ref("risk_taker_sprint_multiplicity_account"),
            "family_count": 1,
            "candidate_count_total": 2,
            "candidate_count_shortlisted": 1,
            "candidate_count_rejected": 1,
            "search_ledger_row_count": 2,
            "generator_types": ["light_ga"],
            "generator_constraints": {"light_ga": "ranking_or_no_trade_filter_only"},
            "default_aggregate_inclusion_allowed": False,
            "default_aggregate_candidate_count": 0,
            "verification_throughput_reregistration_required": True,
            "actual_cash_direct_promotion_allowed": False,
            "tiny_live_direct_promotion_allowed": False,
            "separate_ledger": True,
            "separate_holdout": True,
            "separate_multiplicity_account": True,
            "promotion_debt": [
                {
                    "debt_code": "RE_REGISTER_UNDER_VERIFICATION_THROUGHPUT",
                    "status": "OUTSTANDING",
                    "blocks_actual_cash": True,
                    "message": "Re-register the candidate under verification_throughput.",
                }
            ],
            "boundary": {
                "actual_cash": False,
                "permits_live_order": False,
                "permits_paper_order": False,
                "permits_tiny_live": False,
                "permits_actual_cash": False,
                "production_exchange_write_used": False,
                "live_order_submitted": False,
                "wallet_used": False,
                "signing_used": False,
                "default_aggregate_mixed": False,
                "sprint_positive_result_promoted": False,
            },
        },
    )
    return path


def _evidence_packet_payload() -> dict:
    return {
        "schema_version": "profit_core_evidence_packet.v1",
        "packet_id": "idea-cand-001-profit-core-evidence-packet",
        "generated_at": "2026-07-01T06:18:00Z",
        "producer": {"tool": "sis", "command": "edge-candidate-evidence-packet-build"},
        "candidate_id": "idea-cand-001",
        "source_refs": [_artifact_ref("virtual_gate")],
        "claims": [],
        "claim_findings": [],
        "machine_summary": {
            "candidate_id": "idea-cand-001",
            "bridge_status": "BRIDGED_TECHNICAL_ONLY",
            "backtest_gate_state": "SHORTLIST_FOR_VIRTUAL",
            "virtual_gate_state": "LOCAL_MOCK_VERIFIED",
            "cash_metric_basis": "virtual_exchange",
            "actual_cash_available": False,
            "actual_cash": False,
            "permits_live_order": False,
            "production_exchange_write_used": False,
            "live_order_submitted": False,
            "profit_evidence": False,
        },
        "boundary": {
            "actual_cash": False,
            "permits_live_order": False,
            "permits_paper_order": False,
            "permits_actual_cash": False,
            "production_exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "llm_api_used": False,
        },
    }


def _readiness_plan_payload() -> dict:
    return {
        "measurement_id": "tiny-actual-cash-idea-cand-001",
        "risk_limits": {
            "max_notional_usd": "10",
            "max_daily_loss_usd": "3",
            "max_order_count": 2,
            "max_position_count": 1,
            "leverage_cap": "1",
        },
        "account_controls": {
            "isolated_margin_required": True,
            "withdrawal_disabled_required": True,
            "ip_restriction_required": True,
            "credential_storage_confirmed": True,
            "credential_created": False,
            "credential_used": False,
            "credential_use_allowed": False,
        },
        "operational_controls": {
            "flat_reconciliation_steps": ["close all positions", "verify cash ledger flat"],
            "rollback_steps": ["cancel open orders", "disable execution workflow"],
            "kill_switch_steps": ["stop after one reject", "stop on connectivity ambiguity"],
            "stop_conditions": ["daily loss reached", "terms or jurisdiction mismatch"],
        },
        "venue_terms_jurisdiction_recheck": {
            "required": True,
            "official_docs_required": True,
            "jurisdiction_acknowledged": True,
            "user_account_conditions_required": True,
            "notes": ["recheck immediately before any separate approval"],
        },
        "approval_controls": {
            "human_approval_required": True,
            "approval_artifact_required": True,
            "dry_run_first_required": True,
        },
    }


def _artifact_ref(role: str) -> dict:
    return {
        "artifact_role": role,
        "path": f"{role}.json",
        "sha256": SHA256_A,
        "schema_version": None,
    }


def test_actual_cash_readiness_packet_complete_still_requires_human_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_and_write_actual_cash_readiness_packet(
        evidence_packet_path=_write_evidence_packet(tmp_path),
        adversarial_review_path=_write_adversarial_review(tmp_path),
        readiness_plan_path=_write_readiness_plan(tmp_path),
        risk_sprint_isolation_path=None,
        out_dir=tmp_path / "readiness",
    )

    packet = result.packet

    assert packet.schema_version == "profit_core_actual_cash_readiness_packet.v1"
    assert packet.candidate_id == "idea-cand-001"
    assert (
        packet.readiness_status
        == ProfitCoreActualCashReadinessStatus.PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL
    )
    assert packet.blockers == []
    assert packet.requires_human_approval is True
    assert packet.packet_is_execution_permission is False
    assert packet.actual_cash_execution_allowed is False
    assert packet.credential_used is False
    assert packet.exchange_write_allowed is False
    assert packet.live_order_submitted is False
    assert packet.risk_limits.max_notional_usd == "10"
    assert packet.account_controls.isolated_margin_required is True
    assert packet.operational_controls.stop_conditions
    assert result.packet_path.exists()


def test_actual_cash_readiness_packet_schema_validates_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    result = build_and_write_actual_cash_readiness_packet(
        evidence_packet_path=_write_evidence_packet(tmp_path),
        adversarial_review_path=_write_adversarial_review(tmp_path),
        readiness_plan_path=_write_readiness_plan(tmp_path),
        risk_sprint_isolation_path=None,
        out_dir=tmp_path / "readiness",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_actual_cash_readiness_packet.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.packet.model_dump(mode="json"))


def test_actual_cash_readiness_missing_controls_blocks_without_granting_permission(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    packet = build_actual_cash_readiness_packet(
        evidence_packet_path=_write_evidence_packet(tmp_path),
        adversarial_review_path=_write_adversarial_review(tmp_path),
        readiness_plan_path=_write_readiness_plan(tmp_path, missing_controls=True),
        risk_sprint_isolation_path=None,
    )

    blocker_codes = {blocker.blocker_code for blocker in packet.blockers}

    assert packet.readiness_status == ProfitCoreActualCashReadinessStatus.BLOCKED_READINESS_CONTROLS
    assert "MISSING_STOP_CONDITION" in blocker_codes
    assert packet.actual_cash_execution_allowed is False
    assert packet.packet_is_execution_permission is False


def test_actual_cash_readiness_rejects_secret_like_plan_material(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    plan_path = _write_readiness_plan(tmp_path)
    payload = _readiness_plan_payload()
    payload["credential_policy"] = {"api_key": "secret-value"}
    write_json_artifact(plan_path, payload)

    with pytest.raises(ActualCashReadinessPacketError, match="secret-like"):
        build_actual_cash_readiness_packet(
            evidence_packet_path=_write_evidence_packet(tmp_path),
            adversarial_review_path=_write_adversarial_review(tmp_path),
            readiness_plan_path=plan_path,
            risk_sprint_isolation_path=None,
        )


def test_actual_cash_readiness_blocks_adversarial_hard_blocker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    packet = build_actual_cash_readiness_packet(
        evidence_packet_path=_write_evidence_packet(tmp_path),
        adversarial_review_path=_write_adversarial_review(tmp_path, hard_blocker_count=1),
        readiness_plan_path=_write_readiness_plan(tmp_path),
        risk_sprint_isolation_path=None,
    )

    assert packet.readiness_status == ProfitCoreActualCashReadinessStatus.BLOCKED_ADVERSARIAL_REVIEW
    assert {blocker.blocker_code for blocker in packet.blockers} == {
        "ADVERSARIAL_REVIEW_HARD_BLOCKER"
    }
    assert packet.actual_cash_execution_allowed is False


def test_actual_cash_readiness_blocks_risk_taker_sprint_promotion_debt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    packet = build_actual_cash_readiness_packet(
        evidence_packet_path=_write_evidence_packet(tmp_path),
        adversarial_review_path=_write_adversarial_review(tmp_path),
        readiness_plan_path=_write_readiness_plan(tmp_path),
        risk_sprint_isolation_path=_write_risk_sprint_isolation(tmp_path),
    )

    assert packet.readiness_status == ProfitCoreActualCashReadinessStatus.BLOCKED_PROMOTION_DEBT
    assert {blocker.blocker_code for blocker in packet.blockers} == {
        "RISK_TAKER_SPRINT_PROMOTION_DEBT"
    }
    assert packet.actual_cash_execution_allowed is False


def test_actual_cash_readiness_cli_writes_packet(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "readiness_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-actual-cash-readiness-packet-build",
            "--evidence-packet",
            str(_write_evidence_packet(tmp_path)),
            "--adversarial-review",
            str(_write_adversarial_review(tmp_path)),
            "--readiness-plan",
            str(_write_readiness_plan(tmp_path)),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "credential_used=false" in result.stdout
    assert "exchange_write_allowed=false" in result.stdout
    assert "actual_cash_execution_allowed=false" in result.stdout
    assert "status=pass" in result.stdout
    assert "readiness_status=PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL" in result.stdout
    assert (out_dir / "profit_core_actual_cash_readiness_packet.json").exists()
