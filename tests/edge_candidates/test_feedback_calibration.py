from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest.artifact_io import sha256_file
from sis.cli import app
from sis.edge_candidates.feedback_calibration import (
    ProfitCoreFeedbackCalibrationStatus,
    build_and_write_feedback_calibration,
    build_feedback_calibration,
)
from sis.strategy_inputs.io import write_json_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64
runner = CliRunner()


def _write_artifacts(tmp_path: Path, *, report_decision: str = "kill") -> dict[str, Path]:
    protocol = tmp_path / "candidate_protocol_manifest.json"
    write_json_artifact(protocol, _protocol_payload())

    multiplicity = tmp_path / "trial_multiplicity_account.json"
    write_json_artifact(multiplicity, _multiplicity_payload())

    report_gate = tmp_path / "profit_core_actual_cash_report_gate.json"
    write_json_artifact(
        report_gate,
        _report_gate_payload(
            protocol_path=protocol,
            multiplicity_path=multiplicity,
            decision=report_decision,
        ),
    )

    feedback_log = tmp_path / "feedback_log.json"
    write_json_artifact(feedback_log, _feedback_log_payload())
    return {
        "protocol": protocol,
        "multiplicity": multiplicity,
        "report_gate": report_gate,
        "feedback_log": feedback_log,
    }


def _protocol_payload() -> dict:
    return {
        "schema_version": "candidate_protocol_manifest.v1",
        "protocol_id": "protocol-v1",
        "mode": "verification_throughput",
        "created_at": "2026-07-01T09:00:00Z",
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
        "account_id": "account-v1",
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


def _artifact_ref(role: str, path: Path, schema_version: str) -> dict:
    return {
        "artifact_role": role,
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "schema_version": schema_version,
    }


def _report_gate_payload(*, protocol_path: Path, multiplicity_path: Path, decision: str) -> dict:
    blockers = []
    report_status = "complete"
    promotion_allowed = decision == "promote"
    if decision == "kill":
        blockers = [
            {
                "blocker_code": "ACTUAL_CASH_EDGE_NEGATIVE",
                "message": "Actual-cash edge over NO_TRADE is negative.",
                "source": "actual_cash_rows",
                "severity": "kill",
            }
        ]
    return {
        "schema_version": "profit_core_actual_cash_report_gate.v1",
        "report_id": "tiny-actual-cash-idea-cand-001-actual-cash-report-gate",
        "recorded_at": "2026-07-01T09:15:00Z",
        "producer": {"tool": "sis", "command": "edge-candidate-actual-cash-report-gate"},
        "candidate_id": "idea-cand-001",
        "measurement_id": "tiny-actual-cash-idea-cand-001",
        "report_status": report_status,
        "decision": decision,
        "promotion_allowed": promotion_allowed,
        "blockers": blockers,
        "source_refs": [
            _artifact_ref("protocol", protocol_path, "candidate_protocol_manifest.v1"),
            _artifact_ref(
                "multiplicity_account", multiplicity_path, "trial_multiplicity_account.v1"
            ),
            {
                "artifact_role": "tiny_actual_cash_measurement",
                "path": "measurement.json",
                "sha256": SHA256_A,
                "schema_version": "profit_core_tiny_actual_cash_measurement.v1",
            },
            {
                "artifact_role": "actual_cash_rows",
                "path": "actual_cash_rows.jsonl",
                "sha256": SHA256_A,
                "schema_version": None,
            },
        ],
        "measurement_ref": {
            "artifact_role": "tiny_actual_cash_measurement",
            "path": "measurement.json",
            "sha256": SHA256_A,
            "schema_version": "profit_core_tiny_actual_cash_measurement.v1",
        },
        "readiness_packet_ref": None,
        "evidence_packet_ref": None,
        "actual_cash_rows_ref": None,
        "protocol_ref": _artifact_ref("protocol", protocol_path, "candidate_protocol_manifest.v1"),
        "multiplicity_account_ref": _artifact_ref(
            "multiplicity_account",
            multiplicity_path,
            "trial_multiplicity_account.v1",
        ),
        "backtest_kill_gate_ref": None,
        "virtual_gate_ref": None,
        "policy": {
            "min_events": 2,
            "max_largest_loss_usd": "25",
            "max_profit_concentration": "0.6",
            "max_operator_burden_minutes": "120",
        },
        "sample_size": {
            "event_count": 2,
            "row_count": 4,
            "measured_row_count": 2,
            "no_trade_row_count": 2,
        },
        "event_diversity": {
            "event_set": ["event-1", "event-2"],
            "event_count": 2,
            "measured_action_set": ["CONTINUATION_LONG"],
            "no_trade_event_set": ["event-1", "event-2"],
        },
        "measured_action": "CONTINUATION_LONG",
        "actual_cash_result_usd": "-1" if decision == "kill" else "9",
        "no_trade_result_usd": "2",
        "actual_cash_edge_over_NO_TRADE": "-3" if decision == "kill" else "7",
        "profit_concentration": "0.5",
        "largest_loss_usd": "-1" if decision == "kill" else "4",
        "operator_burden_minutes": "18",
        "reconcile_mismatch": False,
        "evidence_basis": {
            "actual_cash": {"promotion_metric_authority": True},
            "virtual_exchange": {"promotion_metric_authority": False},
            "simulation": {"promotion_metric_authority": False},
            "estimate": {"promotion_metric_authority": False},
        },
        "actual_cash": True,
        "cash_metric_basis": "actual_cash",
        "order_submitted_by_this_command": False,
        "network_attempted": False,
        "credentials_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "wallet_used": False,
        "signing_used": False,
        "permits_live_order": False,
        "permits_actual_cash_execution": False,
        "boundary": {
            "order_submitted_by_this_command": False,
            "network_attempted": False,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "permits_live_order": False,
            "permits_actual_cash_execution": False,
        },
    }


def _feedback_log_payload(**overrides) -> dict:
    payload = {
        "next_protocol_id": "protocol-v2",
        "next_multiplicity_account_id": "account-v2",
        "next_validation_peek_count": 1,
        "holdout_peek_performed": True,
        "same_family_version_reuse_requested": False,
        "killed_candidates": [
            {
                "candidate_id": "idea-cand-001",
                "reason": "actual cash underperformed NO_TRADE",
            }
        ],
        "actual_execution_failures": [
            {
                "failure_id": "actual-failure-001",
                "candidate_id": "idea-cand-001",
                "failure_type": "operator_burden",
                "summary": "Manual reconciliation burden exceeded expectation.",
            }
        ],
        "generator_updates": ["downweight continuation_long after failed actual-cash sample"],
        "family_event_count_policy_updates": ["raise trend_momentum min_event_count_default"],
        "exclusion_rule_updates": ["exclude candidates with repeated reconciliation mismatch"],
        "cost_model_updates": ["increase fee and funding stress assumption"],
        "operator_burden_updates": ["require operator minutes estimate before P9"],
    }
    payload.update(overrides)
    return payload


def test_feedback_calibration_ready_for_next_protocol_review(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)

    result = build_and_write_feedback_calibration(
        protocol_path=paths["protocol"],
        multiplicity_account_path=paths["multiplicity"],
        report_gate_path=paths["report_gate"],
        feedback_log_path=paths["feedback_log"],
        out_dir=tmp_path / "feedback_calibration",
    )
    calibration = result.calibration

    assert calibration.schema_version == "profit_core_feedback_threshold_calibration.v1"
    assert calibration.calibration_status == (
        ProfitCoreFeedbackCalibrationStatus.READY_FOR_NEXT_PROTOCOL_REVIEW
    )
    assert calibration.next_protocol_id == "protocol-v2"
    assert calibration.next_multiplicity_account_id == "account-v2"
    assert calibration.failure_summary["killed_candidate_count"] == 1
    assert calibration.failure_summary["actual_execution_failure_count"] == 1
    assert calibration.proposed_updates["family_event_count_policy_updates"]
    assert calibration.auto_applied is False
    assert calibration.protocol_mutated is False
    assert calibration.thresholds_applied is False
    assert result.calibration_path.exists()


def test_feedback_calibration_schema_validates_output(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    result = build_and_write_feedback_calibration(
        protocol_path=paths["protocol"],
        multiplicity_account_path=paths["multiplicity"],
        report_gate_path=paths["report_gate"],
        feedback_log_path=paths["feedback_log"],
        out_dir=tmp_path / "feedback_calibration",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_feedback_threshold_calibration.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.calibration.model_dump(mode="json"))


def test_feedback_calibration_blocks_success_only_feedback(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path, report_decision="promote")
    write_json_artifact(
        paths["feedback_log"],
        _feedback_log_payload(killed_candidates=[], actual_execution_failures=[]),
    )

    calibration = build_feedback_calibration(
        protocol_path=paths["protocol"],
        multiplicity_account_path=paths["multiplicity"],
        report_gate_path=paths["report_gate"],
        feedback_log_path=paths["feedback_log"],
    )

    assert (
        calibration.calibration_status
        == ProfitCoreFeedbackCalibrationStatus.BLOCKED_SUCCESS_ONLY_FEEDBACK
    )
    assert calibration.auto_applied is False


def test_feedback_calibration_blocks_same_protocol_or_trial_account(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    write_json_artifact(
        paths["feedback_log"],
        _feedback_log_payload(
            next_protocol_id="protocol-v1",
            next_multiplicity_account_id="account-v1",
        ),
    )

    calibration = build_feedback_calibration(
        protocol_path=paths["protocol"],
        multiplicity_account_path=paths["multiplicity"],
        report_gate_path=paths["report_gate"],
        feedback_log_path=paths["feedback_log"],
    )

    assert (
        calibration.calibration_status
        == ProfitCoreFeedbackCalibrationStatus.BLOCKED_PROTOCOL_VERSIONING
    )
    assert "NEW_PROTOCOL_REQUIRED" in {blocker.blocker_code for blocker in calibration.blockers}
    assert "NEW_TRIAL_ACCOUNT_REQUIRED" in {
        blocker.blocker_code for blocker in calibration.blockers
    }


def test_feedback_calibration_blocks_holdout_family_reuse(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    write_json_artifact(
        paths["feedback_log"],
        _feedback_log_payload(same_family_version_reuse_requested=True),
    )

    calibration = build_feedback_calibration(
        protocol_path=paths["protocol"],
        multiplicity_account_path=paths["multiplicity"],
        report_gate_path=paths["report_gate"],
        feedback_log_path=paths["feedback_log"],
    )

    assert (
        calibration.calibration_status == ProfitCoreFeedbackCalibrationStatus.BLOCKED_HOLDOUT_REUSE
    )
    assert "HOLDOUT_PEEK_SAME_FAMILY_REUSE" in {
        blocker.blocker_code for blocker in calibration.blockers
    }


def test_feedback_calibration_blocks_unadvanced_validation_peek_count(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    write_json_artifact(paths["feedback_log"], _feedback_log_payload(next_validation_peek_count=0))

    calibration = build_feedback_calibration(
        protocol_path=paths["protocol"],
        multiplicity_account_path=paths["multiplicity"],
        report_gate_path=paths["report_gate"],
        feedback_log_path=paths["feedback_log"],
    )

    assert (
        calibration.calibration_status
        == ProfitCoreFeedbackCalibrationStatus.BLOCKED_VALIDATION_PEEK_ACCOUNTING
    )
    assert "VALIDATION_PEEK_COUNT_NOT_ADVANCED" in {
        blocker.blocker_code for blocker in calibration.blockers
    }


def test_feedback_calibration_cli_writes_artifact(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    out_dir = tmp_path / "feedback_calibration_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-feedback-calibration-build",
            "--protocol",
            str(paths["protocol"]),
            "--multiplicity-account",
            str(paths["multiplicity"]),
            "--report-gate",
            str(paths["report_gate"]),
            "--feedback-log",
            str(paths["feedback_log"]),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "auto_applied=false" in result.stdout
    assert "protocol_mutated=false" in result.stdout
    assert "thresholds_applied=false" in result.stdout
    assert (out_dir / "profit_core_feedback_threshold_calibration.json").exists()
