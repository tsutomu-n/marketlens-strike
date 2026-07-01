from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest.artifact_io import sha256_file
from sis.cli import app
from sis.edge_candidates.backtest_kill_gate import (
    BacktestKillGateInput,
    build_backtest_kill_gate,
)
from sis.edge_candidates.evidence_packet import (
    ProfitCoreClaim,
    build_and_write_profit_core_evidence_packet,
    build_profit_core_evidence_packet,
)
from sis.edge_candidates.virtual_execution_gate import (
    build_and_write_virtual_execution_gate,
)
from sis.strategy_inputs.io import write_json_artifact

from strategy_idea_candidates.fixtures import valid_candidate_set_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64
runner = CliRunner()


def _write_artifacts(tmp_path: Path) -> dict[str, Path]:
    candidate_set_path = tmp_path / "candidate_set.json"
    write_json_artifact(candidate_set_path, valid_candidate_set_payload())

    protocol_path = tmp_path / "protocol.json"
    write_json_artifact(protocol_path, _protocol_payload())

    multiplicity_path = tmp_path / "trial_multiplicity_account.json"
    write_json_artifact(multiplicity_path, _multiplicity_payload())

    bridge_path = tmp_path / "authoring_bridge.json"
    write_json_artifact(
        bridge_path,
        _bridge_payload(candidate_set_path=candidate_set_path, multiplicity_path=multiplicity_path),
    )

    backtest_kill_gate_path = tmp_path / "backtest_kill_gate.json"
    write_json_artifact(backtest_kill_gate_path, _backtest_kill_gate_payload())

    factory_summary_path = tmp_path / "edge_candidate_factory_summary.json"
    write_json_artifact(
        factory_summary_path,
        _factory_summary_payload(
            candidate_set_path=candidate_set_path,
            multiplicity_path=multiplicity_path,
        ),
    )

    virtual_gate = build_and_write_virtual_execution_gate(
        candidate_set_path=candidate_set_path,
        factory_summary_path=factory_summary_path,
        multiplicity_account_path=multiplicity_path,
        backtest_kill_gate_path=backtest_kill_gate_path,
        candidate_id="idea-cand-001",
        out_dir=tmp_path / "virtual_gate",
    )

    claims_path = tmp_path / "claims.json"
    write_json_artifact(claims_path, {"claims": _claim_payloads()})
    risk_review_path = tmp_path / "risk_review_source.json"
    write_json_artifact(risk_review_path, {"schema_version": "risk_review_source_stub.v1"})
    return {
        "protocol": protocol_path,
        "candidate_set": candidate_set_path,
        "bridge": bridge_path,
        "multiplicity": multiplicity_path,
        "backtest_kill_gate": backtest_kill_gate_path,
        "virtual_gate": virtual_gate.gate_path,
        "claims": claims_path,
        "risk_review": risk_review_path,
    }


def _protocol_payload() -> dict:
    return {
        "schema_version": "candidate_protocol_manifest.v1",
        "protocol_id": "ndx-verification-001",
        "mode": "verification_throughput",
        "created_at": "2026-06-30T11:36:00Z",
        "target_market": "equity_index",
        "target_venue_family": "local_research",
        "families": [
            {
                "family_id": "trend_momentum",
                "hypothesis": "Trend continuation may persist after validation.",
                "generator_type": "classical_rule",
            }
        ],
        "parameter_spaces": {"trend_momentum": {"lookback": [20], "threshold_z": [1.5]}},
        "objective": {"primary": "after_cost_edge_over_no_trade", "benchmark": "NO_TRADE"},
        "exclusion_rules": ["no live order"],
        "sealed_holdout_definition": {
            "window_id": "holdout-2026-q3",
            "start": "2026-07-01T00:00:00Z",
            "end": "2026-09-30T23:59:59Z",
            "peek_policy": "winner-only once",
        },
        "family_event_count_policy": {
            "trend_momentum": {
                "min_event_count_default": 100,
                "insufficient_data_state": "INCONCLUSIVE_DATA",
            }
        },
        "source_requirements": [
            {"source_id": "ndx_ohlcv_daily", "schema_version": "market_ohlcv.v1", "required": True}
        ],
        "venue_execution_constraints": {"max_leverage": 1},
        "llm_policy": {"role": "adversarial_finding_only", "approval_allowed": False},
        "permits_actual_cash": False,
        "permits_live_order": False,
    }


def _multiplicity_payload() -> dict:
    return {
        "schema_version": "trial_multiplicity_account.v1",
        "account_id": "ndx-candidate-set-001-trial-multiplicity",
        "mode": "verification_throughput",
        "candidate_count_total": 2,
        "candidate_count_shortlisted": 1,
        "family_count": 1,
        "family_trial_count": {"trend_momentum": 2},
        "parameter_grid_hashes": {"trend_momentum": SHA256_A},
        "effective_trial_count": 2,
        "correlation_cluster_count": 1,
        "validation_peek_count": 0,
        "rerank_count": 0,
        "sealed_test_used_for_selection": False,
        "success_only_reporting": False,
        "raw_p_value_count": 1,
        "fdr_status": "AVAILABLE",
        "pbo_status": "NOT_ESTIMABLE",
        "dsr_status": "NOT_ESTIMABLE",
        "white_reality_check_status": "NOT_ESTIMABLE",
        "not_estimable_reasons": [
            "PBO_NOT_ESTIMABLE_FOLD_OUTCOMES_MISSING",
            "DSR_NOT_ESTIMABLE_RETURN_DISTRIBUTION_MISSING",
            "WHITE_REALITY_CHECK_NOT_ESTIMABLE_BOOTSTRAP_SERIES_MISSING",
        ],
    }


def _bridge_payload(*, candidate_set_path: Path, multiplicity_path: Path) -> dict:
    return {
        "schema_version": "strategy_idea_candidate_authoring_bridge.v1",
        "manifest_id": "bridge-001",
        "created_at": "2026-07-01T05:54:00Z",
        "producer": {"tool": "sis", "command": "strategy-idea-candidates-authoring-bridge"},
        "candidate_set_id": "ndx-candidate-set-001",
        "candidate_set_path": candidate_set_path.as_posix(),
        "candidate_set_sha256": sha256_file(candidate_set_path),
        "export_manifest_path": "export_manifest.json",
        "export_manifest_sha256": SHA256_A,
        "ledger_path": "search_ledger.jsonl",
        "ledger_sha256": SHA256_A,
        "protocol_manifest_ref": {
            "schema_version": "candidate_protocol_manifest.v1",
            "path": "protocol.json",
            "sha256": SHA256_A,
        },
        "multiplicity_account_ref": {
            "schema_version": "trial_multiplicity_account.v1",
            "path": multiplicity_path.as_posix(),
            "sha256": sha256_file(multiplicity_path),
        },
        "prep_watchdeck_root": "prep",
        "candidates": [
            {
                "candidate_id": "idea-cand-001",
                "family": "trend_momentum",
                "status": "BRIDGED_TECHNICAL_ONLY",
                "symbols": ["NDX"],
                "blockers": [],
                "source_statuses": ["SOURCE_AVAILABLE"],
                "artifacts": {},
                "backtest_kill_gate_state": "SHORTLIST_FOR_VIRTUAL",
                "profit_core_blocker_codes": [],
            }
        ],
        "summary": {
            "candidate_count": 1,
            "status_counts": {"BRIDGED_TECHNICAL_ONLY": 1},
            "bridged_count": 1,
            "blocked_count": 0,
            "candidate_scoped_outputs": True,
            "actual_cash_result_available": False,
        },
        "known_gaps": [],
        "boundary": {
            "permits_live_order": False,
            "permits_paper_candidate": False,
            "permits_paper_intent_preview": False,
            "auto_promote": False,
            "generated_strategy_idea_is_final": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def _backtest_kill_gate_payload() -> dict:
    gate_input = BacktestKillGateInput.model_validate(
        {
            "candidate_id": "idea-cand-001",
            "mode": "verification_throughput",
            "family_id": "trend_momentum",
            "event_count": 120,
            "closed_trade_count": 80,
            "no_trade_comparison_present": True,
            "after_cost_edge_over_no_trade": 1.2,
            "stress_edge_over_no_trade": 0.4,
            "largest_loss_usd": -12.5,
            "profit_concentration": 0.25,
            "regime_stability": "PASS",
            "source_gap_count": 0,
            "unexecutable_reason_count": 0,
            "selection_adjustment_status": "AVAILABLE",
            "family_event_count_policy": {
                "min_event_count_default": 100,
                "insufficient_data_state": "INCONCLUSIVE_DATA",
            },
            "execution_candidate": True,
        }
    )
    return build_backtest_kill_gate(
        gate_input,
        gate_id="backtest-gate-001",
        evaluated_at="2026-07-01T05:54:00Z",
    ).model_dump(mode="json")


def _factory_summary_payload(*, candidate_set_path: Path, multiplicity_path: Path) -> dict:
    return {
        "schema_version": "edge_candidate_factory_summary.v1",
        "protocol_ref": {
            "protocol_id": "ndx-verification-001",
            "mode": "verification_throughput",
            "path": "protocol.json",
            "sha256": SHA256_A,
        },
        "artifact_refs": {
            "candidate_set_path": candidate_set_path.as_posix(),
            "candidate_set_sha256": sha256_file(candidate_set_path),
            "multiplicity_account_path": multiplicity_path.as_posix(),
            "multiplicity_account_sha256": sha256_file(multiplicity_path),
        },
        "candidate_count_total": 2,
        "candidate_count_shortlisted": 1,
        "candidate_count_rejected": 1,
        "best_only_report": False,
        "success_only_reporting": False,
        "sealed_test_used_for_selection": False,
        "unexecutable_reason_count": 0,
        "boundary": {
            "actual_cash": False,
            "permits_live_order": False,
            "live_order_submitted": False,
            "production_exchange_write_used": False,
        },
    }


def _claim_payloads() -> list[dict]:
    return [
        {
            "claim_id": "claim-supported-virtual",
            "claim_type": "virtual_execution_verified",
            "claimed": True,
            "requested_evidence_basis": "virtual_exchange",
            "comparison_ref": "NO_TRADE",
            "text": "Local virtual lifecycle passed.",
        },
        {
            "claim_id": "claim-missing-comparison",
            "claim_type": "after_cost_edge_over_no_trade",
            "claimed": True,
            "requested_evidence_basis": "backtest",
            "comparison_ref": "",
            "text": "There is after-cost edge.",
        },
        {
            "claim_id": "claim-basis-mismatch",
            "claim_type": "virtual_execution_verified",
            "claimed": True,
            "requested_evidence_basis": "actual_cash",
            "comparison_ref": "NO_TRADE",
            "text": "Virtual lifecycle proves cash edge.",
        },
        {
            "claim_id": "claim-actual-cash",
            "claim_type": "actual_cash_result",
            "claimed": True,
            "requested_evidence_basis": "actual_cash",
            "comparison_ref": "NO_TRADE",
            "text": "Actual cash result is available.",
        },
        {
            "claim_id": "claim-unsupported",
            "claim_type": "moonshot_profit",
            "claimed": True,
            "requested_evidence_basis": "backtest",
            "comparison_ref": "NO_TRADE",
            "text": "Unsupported claim.",
        },
    ]


def test_evidence_packet_flags_claim_diff_findings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)

    result = build_and_write_profit_core_evidence_packet(
        protocol_path=paths["protocol"],
        candidate_set_path=paths["candidate_set"],
        bridge_manifest_path=paths["bridge"],
        multiplicity_account_path=paths["multiplicity"],
        backtest_kill_gate_path=paths["backtest_kill_gate"],
        virtual_gate_path=paths["virtual_gate"],
        claims_path=paths["claims"],
        risk_review_source_paths=[paths["risk_review"]],
        candidate_id="idea-cand-001",
        out_dir=tmp_path / "evidence_packet",
    )

    packet = result.packet
    finding_codes = {finding.finding_code for finding in packet.claim_findings}
    severity_by_code = {finding.finding_code: finding.severity for finding in packet.claim_findings}

    assert packet.schema_version == "profit_core_evidence_packet.v1"
    assert packet.machine_summary["backtest_gate_state"] == "SHORTLIST_FOR_VIRTUAL"
    assert packet.machine_summary["virtual_gate_state"] == "LOCAL_MOCK_VERIFIED"
    assert packet.machine_summary["actual_cash_available"] is False
    assert packet.machine_summary["no_trade_comparison_present"] is True
    assert packet.machine_summary["profit_evidence"] is False
    assert packet.boundary["actual_cash"] is False
    assert packet.boundary["permits_live_order"] is False
    assert packet.boundary["production_exchange_write_used"] is False
    assert {
        "UNSUPPORTED_CLAIM",
        "MISSING_COMPARISON",
        "EVIDENCE_BASIS_MISMATCH",
        "ACTUAL_CASH_OVERCLAIM",
    }.issubset(finding_codes)
    assert severity_by_code["ACTUAL_CASH_OVERCLAIM"] == "BLOCKER"
    assert any(ref.artifact_role == "risk_review_source" for ref in packet.source_refs)
    assert result.packet_path.exists()


def test_evidence_packet_schema_validates_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    result = build_and_write_profit_core_evidence_packet(
        protocol_path=paths["protocol"],
        candidate_set_path=paths["candidate_set"],
        bridge_manifest_path=paths["bridge"],
        multiplicity_account_path=paths["multiplicity"],
        backtest_kill_gate_path=paths["backtest_kill_gate"],
        virtual_gate_path=paths["virtual_gate"],
        claims_path=paths["claims"],
        risk_review_source_paths=[paths["risk_review"]],
        candidate_id="idea-cand-001",
        out_dir=tmp_path / "evidence_packet",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_evidence_packet.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.packet.model_dump(mode="json"))


def test_evidence_packet_builder_without_claims_reports_no_findings(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)

    packet = build_profit_core_evidence_packet(
        protocol_path=paths["protocol"],
        candidate_set_path=paths["candidate_set"],
        bridge_manifest_path=paths["bridge"],
        multiplicity_account_path=paths["multiplicity"],
        backtest_kill_gate_path=paths["backtest_kill_gate"],
        virtual_gate_path=paths["virtual_gate"],
        claims=[],
        risk_review_source_paths=[],
        candidate_id="idea-cand-001",
    )

    assert packet.claims == []
    assert packet.claim_findings == []
    assert packet.machine_summary["claim_count"] == 0


def test_evidence_packet_cli_writes_packet(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    out_dir = tmp_path / "evidence_packet_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-evidence-packet-build",
            "--protocol",
            str(paths["protocol"]),
            "--candidate-set",
            str(paths["candidate_set"]),
            "--bridge-manifest",
            str(paths["bridge"]),
            "--multiplicity-account",
            str(paths["multiplicity"]),
            "--backtest-kill-gate",
            str(paths["backtest_kill_gate"]),
            "--virtual-gate",
            str(paths["virtual_gate"]),
            "--claims",
            str(paths["claims"]),
            "--risk-review-source",
            str(paths["risk_review"]),
            "--candidate-id",
            "idea-cand-001",
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "network_attempted=false" in result.stdout
    assert "llm_api_used=false" in result.stdout
    assert "actual_cash=false" in result.stdout
    assert "finding_count=4" in result.stdout
    assert (out_dir / "profit_core_evidence_packet.json").exists()


def test_profit_core_claim_rejects_blank_claim_id() -> None:
    claim = _claim_payloads()[0]
    claim["claim_id"] = ""

    try:
        ProfitCoreClaim.model_validate(claim)
    except ValueError as exc:
        assert "claim_id" in str(exc)
    else:
        raise AssertionError("blank claim_id should fail")
