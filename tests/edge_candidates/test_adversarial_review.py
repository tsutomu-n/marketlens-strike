from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.edge_candidates.adversarial_review import (
    ProfitCoreAdversarialFinding,
    ProfitCoreAdversarialReviewStatus,
    build_and_write_profit_core_adversarial_review,
    build_profit_core_adversarial_review,
)
from sis.strategy_inputs.io import write_json_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64
runner = CliRunner()


def _write_evidence_packet(tmp_path: Path, *, with_findings: bool = True) -> Path:
    path = tmp_path / "profit_core_evidence_packet.json"
    write_json_artifact(path, _evidence_packet_payload(with_findings=with_findings))
    return path


def _write_manual_review(tmp_path: Path) -> Path:
    path = tmp_path / "manual_review.json"
    write_json_artifact(
        path,
        {
            "findings": [
                {
                    "finding_id": "manual-human-review",
                    "status": "HUMAN_REVIEW_REQUIRED",
                    "severity": "WARNING",
                    "message": "Manual reviewer wants operator review before any promotion.",
                    "evidence_refs": [{"ref_type": "machine_summary", "ref_id": "bridge_status"}],
                }
            ]
        },
    )
    return path


def _evidence_packet_payload(*, with_findings: bool) -> dict:
    claim_findings = []
    if with_findings:
        claim_findings = [
            {
                "claim_id": "claim-missing-comparison",
                "finding_code": "MISSING_COMPARISON",
                "severity": "WARNING",
                "message": "NO_TRADE comparison is missing.",
            },
            {
                "claim_id": "claim-actual-cash",
                "finding_code": "ACTUAL_CASH_OVERCLAIM",
                "severity": "BLOCKER",
                "message": "Actual-cash evidence is not available.",
            },
        ]
    return {
        "schema_version": "profit_core_evidence_packet.v1",
        "packet_id": "idea-cand-001-profit-core-evidence-packet",
        "generated_at": "2026-07-01T06:18:00Z",
        "producer": {"tool": "sis", "command": "edge-candidate-evidence-packet-build"},
        "candidate_id": "idea-cand-001",
        "source_refs": [
            {
                "artifact_role": "virtual_gate",
                "path": "virtual_execution_gate.json",
                "sha256": SHA256_A,
                "schema_version": "virtual_execution_gate.v1",
            }
        ],
        "claims": [],
        "claim_findings": claim_findings,
        "machine_summary": {
            "protocol_id": "ndx-verification-001",
            "mode": "verification_throughput",
            "candidate_set_id": "ndx-candidate-set-001",
            "candidate_id": "idea-cand-001",
            "candidate_decision": "SHORTLISTED",
            "bridge_status": "BRIDGED_TECHNICAL_ONLY",
            "backtest_gate_state": "SHORTLIST_FOR_VIRTUAL",
            "no_trade_comparison_present": True,
            "virtual_gate_state": "LOCAL_MOCK_VERIFIED",
            "cash_metric_basis": "virtual_exchange",
            "evidence_bases": ["backtest", "virtual_exchange"],
            "actual_cash_available": False,
            "actual_cash": False,
            "permits_live_order": False,
            "production_exchange_write_used": False,
            "live_order_submitted": False,
            "profit_evidence": False,
            "claim_count": 0,
            "finding_count": len(claim_findings),
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


def test_adversarial_review_converts_packet_findings_without_permission(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = _write_evidence_packet(tmp_path)

    result = build_and_write_profit_core_adversarial_review(
        evidence_packet_path=packet_path,
        manual_review_path=None,
        out_dir=tmp_path / "review",
    )

    review = result.review
    statuses = {finding.status for finding in review.findings}
    hard_blockers = [finding for finding in review.findings if finding.hard_blocker]

    assert review.schema_version == "profit_core_adversarial_review.v1"
    assert review.review_status == ProfitCoreAdversarialReviewStatus.OVERCLAIM_FLAG
    assert ProfitCoreAdversarialReviewStatus.NEEDS_MORE_EVIDENCE in statuses
    assert ProfitCoreAdversarialReviewStatus.OVERCLAIM_FLAG in statuses
    assert len(hard_blockers) == 1
    assert hard_blockers[0].machine_checkable is True
    assert review.approval_allowed is False
    assert review.permission_allowed is False
    assert review.no_additional_blocker_is_approval is False
    assert review.boundary["llm_api_used"] is False
    assert review.boundary["external_send_performed"] is False
    assert review.boundary["actual_cash_decision_allowed"] is False
    assert result.review_path.exists()


def test_adversarial_review_schema_validates_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = build_and_write_profit_core_adversarial_review(
        evidence_packet_path=_write_evidence_packet(tmp_path),
        manual_review_path=_write_manual_review(tmp_path),
        out_dir=tmp_path / "review",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_adversarial_review.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.review.model_dump(mode="json"))


def test_adversarial_review_without_findings_is_not_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    review = build_profit_core_adversarial_review(
        evidence_packet_path=_write_evidence_packet(tmp_path, with_findings=False),
        manual_review_path=None,
    )

    assert review.review_status == ProfitCoreAdversarialReviewStatus.NO_ADDITIONAL_BLOCKER_FOUND
    assert review.findings == []
    assert review.approval_allowed is False
    assert review.no_additional_blocker_is_approval is False


def test_manual_review_finding_is_non_hard_blocking(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    review = build_profit_core_adversarial_review(
        evidence_packet_path=_write_evidence_packet(tmp_path, with_findings=False),
        manual_review_path=_write_manual_review(tmp_path),
    )

    assert review.review_status == ProfitCoreAdversarialReviewStatus.HUMAN_REVIEW_REQUIRED
    assert review.manual_finding_count == 1
    assert review.findings[0].machine_checkable is False
    assert review.findings[0].hard_blocker is False


def test_manual_review_rejects_hard_blocker_attempt(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manual_path = tmp_path / "manual_review.json"
    write_json_artifact(
        manual_path,
        {
            "findings": [
                {
                    "finding_id": "manual-hard-blocker",
                    "status": "HUMAN_REVIEW_REQUIRED",
                    "severity": "ERROR",
                    "message": "Manual text must not become a hard blocker.",
                    "machine_checkable": False,
                    "hard_blocker": True,
                }
            ]
        },
    )

    try:
        build_profit_core_adversarial_review(
            evidence_packet_path=_write_evidence_packet(tmp_path, with_findings=False),
            manual_review_path=manual_path,
        )
    except ValueError as exc:
        assert "manual findings cannot set hard_blocker" in str(exc)
    else:
        raise AssertionError("manual hard_blocker attempt should fail")


def test_adversarial_finding_rejects_approval_status() -> None:
    try:
        ProfitCoreAdversarialFinding.model_validate(
            {
                "finding_id": "bad-approval",
                "status": "APPROVED",
                "severity": "INFO",
                "message": "Approval is not a valid adversarial review status.",
                "source": "MANUAL_ADVERSARIAL_REVIEW",
                "evidence_refs": [],
                "machine_checkable": False,
                "hard_blocker": False,
            }
        )
    except ValueError as exc:
        assert "APPROVED" in str(exc)
    else:
        raise AssertionError("approval status should fail")


def test_adversarial_review_cli_writes_review(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "review_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-adversarial-review-record",
            "--evidence-packet",
            str(_write_evidence_packet(tmp_path)),
            "--manual-review",
            str(_write_manual_review(tmp_path)),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "review_status=OVERCLAIM_FLAG" in result.stdout
    assert "llm_api_used=false" in result.stdout
    assert "external_send_performed=false" in result.stdout
    assert "approval_allowed=false" in result.stdout
    assert "hard_blocker_count=1" in result.stdout
    assert (out_dir / "profit_core_adversarial_review.json").exists()
