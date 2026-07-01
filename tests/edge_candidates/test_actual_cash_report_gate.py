from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest.artifact_io import sha256_file
from sis.cli import app
from sis.edge_candidates.actual_cash_report_gate import (
    ActualCashReportGateError,
    ProfitCoreActualCashReportDecision,
    ProfitCoreActualCashReportStatus,
    build_and_write_actual_cash_report_gate,
    build_actual_cash_report_gate,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64
runner = CliRunner()


def _write_artifacts(tmp_path: Path, *, rows: list[dict] | None = None) -> dict[str, Path]:
    evidence_packet = tmp_path / "profit_core_evidence_packet.json"
    write_json_artifact(evidence_packet, _evidence_packet_payload())

    readiness_packet = tmp_path / "profit_core_actual_cash_readiness_packet.json"
    write_json_artifact(
        readiness_packet,
        _readiness_packet_payload(evidence_packet_path=evidence_packet),
    )

    actual_cash_rows = tmp_path / "actual_cash_rows.jsonl"
    _write_rows(actual_cash_rows, rows or _positive_rows())

    stubs = {
        role: tmp_path / f"{role}.json"
        for role in (
            "external_venue_adapter",
            "human_approval",
            "order_intent",
            "submitted_order",
            "fills",
            "fee_funding",
            "cash_ledger",
            "flat_reconciliation",
            "stop_condition",
        )
    }
    for role, path in stubs.items():
        write_json_artifact(
            path, {"schema_version": f"{role}.stub.v1", "candidate_id": "idea-cand-001"}
        )

    measurement = tmp_path / "profit_core_tiny_actual_cash_measurement.json"
    write_json_artifact(
        measurement,
        _measurement_payload(
            readiness_packet_path=readiness_packet,
            actual_cash_rows_path=actual_cash_rows,
            stubs=stubs,
        ),
    )
    return {
        "measurement": measurement,
        "readiness_packet": readiness_packet,
        "evidence_packet": evidence_packet,
        "actual_cash_rows": actual_cash_rows,
    }


def _positive_rows() -> list[dict]:
    return [
        _row("event-1", "CONTINUATION_LONG", "5", "10"),
        _row("event-2", "CONTINUATION_LONG", "4", "8"),
        _row("event-1", "NO_TRADE", "1", "0"),
        _row("event-2", "NO_TRADE", "1", "0"),
    ]


def _row(event_id: str, action: str, value: str, operator_minutes: str) -> dict:
    return {
        "event_id": event_id,
        "action": action,
        "cash_metric_value_usd": value,
        "actual_cash_result_usd": value,
        "cash_metric_basis": "actual_cash",
        "market_adjusted_return": "0",
        "operator_time_minutes": operator_minutes,
        "near_miss": False,
    }


def _write_rows(path: Path, rows: list[dict]) -> None:
    write_text_artifact(path, "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def _artifact_ref(role: str, path: Path, schema_version: str | None = None) -> dict:
    return {
        "artifact_role": role,
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "schema_version": schema_version,
    }


def _evidence_packet_payload(*, candidate_id: str = "idea-cand-001") -> dict:
    return {
        "schema_version": "profit_core_evidence_packet.v1",
        "packet_id": f"{candidate_id}-profit-core-evidence-packet",
        "generated_at": "2026-07-01T06:18:00Z",
        "producer": {"tool": "sis", "command": "edge-candidate-evidence-packet-build"},
        "candidate_id": candidate_id,
        "source_refs": [
            {
                "artifact_role": "protocol",
                "path": "protocol.json",
                "sha256": SHA256_A,
                "schema_version": "candidate_protocol_manifest.v1",
            },
            {
                "artifact_role": "multiplicity_account",
                "path": "trial_multiplicity_account.json",
                "sha256": SHA256_A,
                "schema_version": "trial_multiplicity_account.v1",
            },
            {
                "artifact_role": "backtest_kill_gate",
                "path": "backtest_kill_gate.json",
                "sha256": SHA256_A,
                "schema_version": "backtest_kill_gate.v1",
            },
            {
                "artifact_role": "virtual_gate",
                "path": "virtual_gate.json",
                "sha256": SHA256_A,
                "schema_version": "virtual_execution_gate.v1",
            },
        ],
        "claims": [],
        "claim_findings": [],
        "machine_summary": {
            "candidate_id": candidate_id,
            "bridge_status": "BRIDGED_TECHNICAL_ONLY",
            "backtest_gate_state": "SHORTLIST_FOR_VIRTUAL",
            "virtual_gate_state": "LOCAL_MOCK_VERIFIED",
            "cash_metric_basis": "virtual_exchange",
            "actual_cash_available": False,
            "actual_cash": False,
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


def _readiness_packet_payload(
    *,
    evidence_packet_path: Path,
    candidate_id: str = "idea-cand-001",
    measurement_id: str = "tiny-actual-cash-idea-cand-001",
) -> dict:
    adversarial_path = evidence_packet_path.parent / "profit_core_adversarial_review.json"
    readiness_plan_path = evidence_packet_path.parent / "actual_cash_readiness_plan.json"
    write_json_artifact(adversarial_path, {"schema_version": "profit_core_adversarial_review.v1"})
    write_json_artifact(
        readiness_plan_path, {"schema_version": "actual_cash_readiness_plan.stub.v1"}
    )
    refs = [
        _artifact_ref("evidence_packet", evidence_packet_path, "profit_core_evidence_packet.v1"),
        _artifact_ref("adversarial_review", adversarial_path, "profit_core_adversarial_review.v1"),
        _artifact_ref("readiness_plan", readiness_plan_path, None),
    ]
    return {
        "schema_version": "profit_core_actual_cash_readiness_packet.v1",
        "packet_id": f"{candidate_id}-actual-cash-readiness-packet",
        "recorded_at": "2026-07-01T07:00:00Z",
        "producer": {"tool": "sis", "command": "edge-candidate-actual-cash-readiness-packet-build"},
        "candidate_id": candidate_id,
        "measurement_id": measurement_id,
        "source_refs": refs,
        "evidence_packet_ref": refs[0],
        "adversarial_review_ref": refs[1],
        "readiness_plan_ref": refs[2],
        "risk_sprint_isolation_ref": None,
        "readiness_status": "PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL",
        "blockers": [],
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
            "flat_reconciliation_steps": ["verify flat"],
            "rollback_steps": ["stop workflow"],
            "kill_switch_steps": ["stop on mismatch"],
            "stop_conditions": ["daily loss"],
        },
        "venue_terms_jurisdiction_recheck": {
            "required": True,
            "official_docs_required": True,
            "jurisdiction_acknowledged": True,
            "user_account_conditions_required": True,
            "notes": ["recheck before separate approval"],
        },
        "approval_controls": {
            "human_approval_required": True,
            "approval_artifact_required": True,
            "dry_run_first_required": True,
        },
        "requires_human_approval": True,
        "packet_is_execution_permission": False,
        "actual_cash_execution_allowed": False,
        "tiny_live_allowed": False,
        "paper_execution_allowed": False,
        "credential_created": False,
        "credential_used": False,
        "credential_use_allowed": False,
        "exchange_write_used": False,
        "exchange_write_allowed": False,
        "live_order_submitted": False,
        "wallet_used": False,
        "signing_used": False,
        "external_send_performed": False,
        "boundary": {
            "actual_cash_execution_allowed": False,
            "tiny_live_allowed": False,
            "paper_execution_allowed": False,
            "credential_created": False,
            "credential_used": False,
            "credential_use_allowed": False,
            "exchange_write_used": False,
            "exchange_write_allowed": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "external_send_performed": False,
            "packet_is_execution_permission": False,
        },
    }


def _measurement_payload(
    *,
    readiness_packet_path: Path,
    actual_cash_rows_path: Path,
    stubs: dict[str, Path],
    status: str = "RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE",
    candidate_id: str = "idea-cand-001",
    measurement_id: str = "tiny-actual-cash-idea-cand-001",
    actual_cash: bool = True,
) -> dict:
    refs = [
        _artifact_ref(
            "readiness_packet", readiness_packet_path, "profit_core_actual_cash_readiness_packet.v1"
        ),
        _artifact_ref(
            "external_venue_adapter",
            stubs["external_venue_adapter"],
            "profit_core_external_venue_adapter_run.v1",
        ),
        _artifact_ref("human_approval", stubs["human_approval"], None),
        _artifact_ref("order_intent", stubs["order_intent"], None),
        _artifact_ref("submitted_order", stubs["submitted_order"], None),
        _artifact_ref("fills", stubs["fills"], None),
        _artifact_ref("fee_funding", stubs["fee_funding"], None),
        _artifact_ref("cash_ledger", stubs["cash_ledger"], "crypto_perp_cash_ledger.v1"),
        _artifact_ref("actual_cash_rows", actual_cash_rows_path, None),
        _artifact_ref("flat_reconciliation", stubs["flat_reconciliation"], None),
        _artifact_ref("stop_condition", stubs["stop_condition"], None),
    ]
    return {
        "schema_version": "profit_core_tiny_actual_cash_measurement.v1",
        "measurement_id": measurement_id,
        "recorded_at": "2026-07-01T08:10:00Z",
        "producer": {
            "tool": "sis",
            "command": "edge-candidate-tiny-actual-cash-measurement-record",
        },
        "candidate_id": candidate_id,
        "measurement_status": status,
        "blockers": []
        if actual_cash
        else [
            {
                "blocker_code": "NON_ACTUAL_CASH_BASIS",
                "message": "not actual cash",
                "source": "actual_cash_rows",
            }
        ],
        "source_refs": refs,
        "readiness_packet_ref": refs[0],
        "external_venue_adapter_ref": refs[1],
        "human_approval_ref": refs[2],
        "order_intent_ref": refs[3],
        "submitted_order_ref": refs[4],
        "fills_ref": refs[5],
        "fee_funding_ref": refs[6],
        "cash_ledger_ref": refs[7],
        "actual_cash_rows_ref": refs[8],
        "flat_reconciliation_ref": refs[9],
        "stop_condition_ref": refs[10],
        "event_set": ["event-1", "event-2"],
        "action_set": ["CONTINUATION_LONG", "NO_TRADE"],
        "row_count": 4,
        "actual_cash_result_usd": "11" if actual_cash else None,
        "cash_ledger_actual_cash_result_usd": "11",
        "no_trade_comparison_present": actual_cash,
        "flat_reconciled": actual_cash,
        "stop_conditions_respected": actual_cash,
        "actual_cash": actual_cash,
        "cash_metric_basis": "actual_cash" if actual_cash else "blocked",
        "order_submitted_by_this_command": False,
        "network_attempted": False,
        "credentials_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "wallet_used": False,
        "signing_used": False,
        "boundary": {
            "order_submitted_by_this_command": False,
            "network_attempted": False,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
        },
    }


def test_actual_cash_report_gate_promotes_positive_actual_cash_edge(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)

    result = build_and_write_actual_cash_report_gate(
        measurement_path=paths["measurement"],
        out_dir=tmp_path / "report_gate",
        min_events=2,
    )
    gate = result.gate

    assert gate.schema_version == "profit_core_actual_cash_report_gate.v1"
    assert gate.candidate_id == "idea-cand-001"
    assert gate.report_status == ProfitCoreActualCashReportStatus.COMPLETE
    assert gate.decision == ProfitCoreActualCashReportDecision.PROMOTE
    assert gate.promotion_allowed is True
    assert gate.actual_cash_edge_over_NO_TRADE == "7"
    assert gate.sample_size["event_count"] == 2
    assert gate.event_diversity["measured_action_set"] == ["CONTINUATION_LONG"]
    assert gate.profit_concentration == "0.5555555555555555555555555556"
    assert gate.largest_loss_usd == "4"
    assert gate.operator_burden_minutes == "18"
    assert gate.reconcile_mismatch is False
    assert gate.evidence_basis["actual_cash"]["promotion_metric_authority"] is True
    assert gate.evidence_basis["virtual_exchange"]["promotion_metric_authority"] is False
    assert gate.network_attempted is False
    assert gate.exchange_write_used is False
    assert gate.live_order_submitted is False
    assert result.gate_path.exists()


def test_actual_cash_report_gate_schema_validates_output(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    result = build_and_write_actual_cash_report_gate(
        measurement_path=paths["measurement"],
        out_dir=tmp_path / "report_gate",
        min_events=2,
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_actual_cash_report_gate.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.gate.model_dump(mode="json"))


def test_actual_cash_report_gate_waits_without_positive_edge(tmp_path: Path) -> None:
    rows = [
        _row("event-1", "CONTINUATION_LONG", "1", "1"),
        _row("event-2", "CONTINUATION_LONG", "1", "1"),
        _row("event-1", "NO_TRADE", "1", "0"),
        _row("event-2", "NO_TRADE", "1", "0"),
    ]
    paths = _write_artifacts(tmp_path, rows=rows)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)

    assert gate.decision == ProfitCoreActualCashReportDecision.WAIT
    assert gate.promotion_allowed is False
    assert gate.actual_cash_edge_over_NO_TRADE == "0"
    assert "ACTUAL_CASH_EDGE_NOT_POSITIVE" in {blocker.blocker_code for blocker in gate.blockers}


def test_actual_cash_report_gate_kills_negative_edge(tmp_path: Path) -> None:
    rows = [
        _row("event-1", "CONTINUATION_LONG", "-1", "1"),
        _row("event-2", "CONTINUATION_LONG", "0", "1"),
        _row("event-1", "NO_TRADE", "1", "0"),
        _row("event-2", "NO_TRADE", "1", "0"),
    ]
    paths = _write_artifacts(tmp_path, rows=rows)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)

    assert gate.decision == ProfitCoreActualCashReportDecision.KILL
    assert gate.promotion_allowed is False
    assert gate.actual_cash_edge_over_NO_TRADE == "-3"


def test_actual_cash_report_gate_waits_for_insufficient_sample_size(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=3)

    assert gate.decision == ProfitCoreActualCashReportDecision.WAIT
    assert gate.promotion_allowed is False
    assert "INSUFFICIENT_EVENT_COUNT" in {blocker.blocker_code for blocker in gate.blockers}


def test_actual_cash_report_gate_waits_for_profit_concentration(tmp_path: Path) -> None:
    rows = [
        _row("event-1", "CONTINUATION_LONG", "9", "1"),
        _row("event-2", "CONTINUATION_LONG", "1", "1"),
        _row("event-1", "NO_TRADE", "0", "0"),
        _row("event-2", "NO_TRADE", "0", "0"),
    ]
    paths = _write_artifacts(tmp_path, rows=rows)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)

    assert gate.decision == ProfitCoreActualCashReportDecision.WAIT
    assert gate.promotion_allowed is False
    assert gate.profit_concentration == "0.9"
    assert "PROFIT_CONCENTRATION_TOO_HIGH" in {blocker.blocker_code for blocker in gate.blockers}


def test_actual_cash_report_gate_kills_largest_loss_breach(tmp_path: Path) -> None:
    rows = [
        _row("event-1", "CONTINUATION_LONG", "-30", "1"),
        _row("event-2", "CONTINUATION_LONG", "50", "1"),
        _row("event-1", "NO_TRADE", "0", "0"),
        _row("event-2", "NO_TRADE", "0", "0"),
    ]
    paths = _write_artifacts(tmp_path, rows=rows)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)

    assert gate.decision == ProfitCoreActualCashReportDecision.KILL
    assert gate.promotion_allowed is False
    assert gate.largest_loss_usd == "-30"
    assert "LARGEST_LOSS_LIMIT_BREACH" in {blocker.blocker_code for blocker in gate.blockers}


def test_actual_cash_report_gate_waits_for_operator_burden(tmp_path: Path) -> None:
    rows = [
        _row("event-1", "CONTINUATION_LONG", "5", "80"),
        _row("event-2", "CONTINUATION_LONG", "4", "80"),
        _row("event-1", "NO_TRADE", "1", "0"),
        _row("event-2", "NO_TRADE", "1", "0"),
    ]
    paths = _write_artifacts(tmp_path, rows=rows)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)

    assert gate.decision == ProfitCoreActualCashReportDecision.WAIT
    assert gate.promotion_allowed is False
    assert gate.operator_burden_minutes == "160"
    assert "OPERATOR_BURDEN_TOO_HIGH" in {blocker.blocker_code for blocker in gate.blockers}


def test_actual_cash_report_gate_waits_for_blocked_p11_measurement(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    payload = json.loads(paths["measurement"].read_text(encoding="utf-8"))
    payload.update(
        _measurement_payload(
            readiness_packet_path=paths["readiness_packet"],
            actual_cash_rows_path=paths["actual_cash_rows"],
            stubs={
                role: tmp_path / f"{role}.json"
                for role in (
                    "external_venue_adapter",
                    "human_approval",
                    "order_intent",
                    "submitted_order",
                    "fills",
                    "fee_funding",
                    "cash_ledger",
                    "flat_reconciliation",
                    "stop_condition",
                )
            },
            status="BLOCKED_NON_ACTUAL_CASH_BASIS",
            actual_cash=False,
        )
    )
    write_json_artifact(paths["measurement"], payload)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)

    assert gate.report_status == ProfitCoreActualCashReportStatus.BLOCKED
    assert gate.decision == ProfitCoreActualCashReportDecision.WAIT
    assert gate.promotion_allowed is False
    assert "P11_MEASUREMENT_NOT_COMPLETE" in {blocker.blocker_code for blocker in gate.blockers}


def test_actual_cash_report_gate_blocks_candidate_lineage_mismatch(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    readiness = _readiness_packet_payload(
        evidence_packet_path=paths["evidence_packet"],
        candidate_id="other-cand",
    )
    write_json_artifact(paths["readiness_packet"], readiness)
    measurement = json.loads(paths["measurement"].read_text(encoding="utf-8"))
    measurement["readiness_packet_ref"] = _artifact_ref(
        "readiness_packet",
        paths["readiness_packet"],
        "profit_core_actual_cash_readiness_packet.v1",
    )
    measurement["source_refs"][0] = measurement["readiness_packet_ref"]
    write_json_artifact(paths["measurement"], measurement)

    gate = build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)

    assert gate.report_status == ProfitCoreActualCashReportStatus.BLOCKED
    assert gate.decision == ProfitCoreActualCashReportDecision.WAIT
    assert gate.promotion_allowed is False
    assert "CANDIDATE_LINEAGE_MISMATCH" in {blocker.blocker_code for blocker in gate.blockers}


def test_actual_cash_report_gate_fails_on_rows_hash_mismatch(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    _write_rows(paths["actual_cash_rows"], [_row("event-1", "NO_TRADE", "0", "0")])

    with pytest.raises(ActualCashReportGateError, match="actual_cash_rows hash mismatch"):
        build_actual_cash_report_gate(measurement_path=paths["measurement"], min_events=2)


def test_actual_cash_report_gate_cli_writes_gate(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    out_dir = tmp_path / "report_gate_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-actual-cash-report-gate",
            "--measurement",
            str(paths["measurement"]),
            "--min-events",
            "2",
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "order_submitted_by_this_command=false" in result.stdout
    assert "status=pass" in result.stdout
    assert "decision=promote" in result.stdout
    assert (out_dir / "profit_core_actual_cash_report_gate.json").exists()
