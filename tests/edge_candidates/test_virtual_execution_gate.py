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
from sis.edge_candidates.virtual_execution_gate import (
    VirtualExecutionEvent,
    VirtualExecutionEventType,
    VirtualExecutionGateInput,
    build_and_write_virtual_execution_gate,
    build_virtual_execution_gate,
    default_local_mock_lifecycle_events,
)
from sis.strategy_inputs.io import write_json_artifact

from strategy_idea_candidates.fixtures import valid_candidate_set_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64
runner = CliRunner()


def _write_p5_artifacts(
    tmp_path: Path, *, kill_state: str = "SHORTLIST_FOR_VIRTUAL"
) -> dict[str, Path]:
    candidate_set_path = tmp_path / "candidate_set.json"
    candidate_set_payload = valid_candidate_set_payload()
    write_json_artifact(candidate_set_path, candidate_set_payload)

    multiplicity_path = tmp_path / "trial_multiplicity_account.json"
    write_json_artifact(multiplicity_path, _multiplicity_payload())

    factory_summary_path = tmp_path / "edge_candidate_factory_summary.json"
    write_json_artifact(
        factory_summary_path,
        _factory_summary_payload(
            candidate_set_path=candidate_set_path,
            multiplicity_path=multiplicity_path,
        ),
    )

    kill_gate_path = tmp_path / "backtest_kill_gate.json"
    write_json_artifact(kill_gate_path, _kill_gate_payload(kill_state=kill_state))
    return {
        "candidate_set": candidate_set_path,
        "multiplicity": multiplicity_path,
        "factory_summary": factory_summary_path,
        "kill_gate": kill_gate_path,
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


def _kill_gate_payload(*, kill_state: str) -> dict:
    payload = {
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
    if kill_state == "KILL":
        payload["after_cost_edge_over_no_trade"] = 0
    if kill_state == "INCONCLUSIVE_DATA":
        payload["no_trade_comparison_present"] = False
    gate = build_backtest_kill_gate(
        BacktestKillGateInput.model_validate(payload),
        gate_id="backtest-gate-001",
        evaluated_at="2026-07-01T05:54:00Z",
    )
    return gate.model_dump(mode="json")


def test_virtual_execution_gate_writes_local_mock_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_p5_artifacts(tmp_path)

    result = build_and_write_virtual_execution_gate(
        candidate_set_path=paths["candidate_set"],
        factory_summary_path=paths["factory_summary"],
        multiplicity_account_path=paths["multiplicity"],
        backtest_kill_gate_path=paths["kill_gate"],
        candidate_id="idea-cand-001",
        out_dir=tmp_path / "virtual_gate",
    )

    payload = json.loads(result.gate_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "virtual_execution_gate.v1"
    assert payload["gate_state"] == "LOCAL_MOCK_VERIFIED"
    assert payload["cash_metric_basis"] == "virtual_exchange"
    assert payload["actual_cash"] is False
    assert payload["permits_live_order"] is False
    assert payload["live_order_submitted"] is False
    assert payload["production_exchange_write_used"] is False
    assert payload["wallet_used"] is False
    assert payload["signing_used"] is False
    assert payload["summary"]["submit_ack_checked"] is True
    assert payload["summary"]["partial_fill_checked"] is True
    assert payload["summary"]["cancel_checked"] is True
    assert payload["summary"]["duplicate_prevention_checked"] is True
    assert payload["summary"]["flat_reconciliation_checked"] is True
    assert "virtual_pnl" not in payload["summary"]


def test_virtual_execution_gate_blocks_killed_and_inconclusive_backtest_gate(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    killed_paths = _write_p5_artifacts(tmp_path / "killed", kill_state="KILL")
    inconclusive_paths = _write_p5_artifacts(
        tmp_path / "inconclusive", kill_state="INCONCLUSIVE_DATA"
    )

    killed = build_and_write_virtual_execution_gate(
        candidate_set_path=killed_paths["candidate_set"],
        factory_summary_path=killed_paths["factory_summary"],
        multiplicity_account_path=killed_paths["multiplicity"],
        backtest_kill_gate_path=killed_paths["kill_gate"],
        candidate_id="idea-cand-001",
        out_dir=tmp_path / "killed_gate",
    )
    inconclusive = build_and_write_virtual_execution_gate(
        candidate_set_path=inconclusive_paths["candidate_set"],
        factory_summary_path=inconclusive_paths["factory_summary"],
        multiplicity_account_path=inconclusive_paths["multiplicity"],
        backtest_kill_gate_path=inconclusive_paths["kill_gate"],
        candidate_id="idea-cand-001",
        out_dir=tmp_path / "inconclusive_gate",
    )

    assert killed.gate.gate_state == "BLOCKED_BY_BACKTEST_GATE"
    assert "backtest_gate_not_shortlist_for_virtual" in killed.gate.blocker_codes
    assert inconclusive.gate.gate_state == "BLOCKED_BY_BACKTEST_GATE"
    assert "backtest_gate_not_shortlist_for_virtual" in inconclusive.gate.blocker_codes


def test_virtual_execution_gate_blocks_rejected_candidate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_p5_artifacts(tmp_path)

    result = build_and_write_virtual_execution_gate(
        candidate_set_path=paths["candidate_set"],
        factory_summary_path=paths["factory_summary"],
        multiplicity_account_path=paths["multiplicity"],
        backtest_kill_gate_path=paths["kill_gate"],
        candidate_id="idea-cand-002",
        out_dir=tmp_path / "virtual_gate",
    )

    assert result.gate.gate_state == "BLOCKED_BY_CANDIDATE_STATE"
    assert "candidate_not_shortlisted" in result.gate.blocker_codes


def test_virtual_execution_gate_state_machine_blocks_bad_lifecycle() -> None:
    duplicate = build_virtual_execution_gate(
        VirtualExecutionGateInput(
            candidate_id="idea-cand-001",
            mode="verification_throughput",
            candidate_decision="SHORTLISTED",
            backtest_gate_state="SHORTLIST_FOR_VIRTUAL",
            multiplicity_success_only_reporting=False,
            multiplicity_sealed_test_used_for_selection=False,
            unexecutable_reason_count=0,
            lifecycle_events=[
                VirtualExecutionEvent(event_type=VirtualExecutionEventType.SUBMIT_ACK),
                VirtualExecutionEvent(event_type=VirtualExecutionEventType.SUBMIT_ACK),
                *default_local_mock_lifecycle_events()[1:],
            ],
        ),
        gate_id="virtual-gate-001",
        evaluated_at="2026-07-01T05:54:00Z",
    )
    unknown = build_virtual_execution_gate(
        VirtualExecutionGateInput(
            candidate_id="idea-cand-001",
            mode="verification_throughput",
            candidate_decision="SHORTLISTED",
            backtest_gate_state="SHORTLIST_FOR_VIRTUAL",
            multiplicity_success_only_reporting=False,
            multiplicity_sealed_test_used_for_selection=False,
            unexecutable_reason_count=0,
            lifecycle_events=[
                VirtualExecutionEvent(event_type=VirtualExecutionEventType.UNKNOWN_STATE),
            ],
        ),
        gate_id="virtual-gate-002",
        evaluated_at="2026-07-01T05:54:00Z",
    )
    mismatch = build_virtual_execution_gate(
        VirtualExecutionGateInput(
            candidate_id="idea-cand-001",
            mode="verification_throughput",
            candidate_decision="SHORTLISTED",
            backtest_gate_state="SHORTLIST_FOR_VIRTUAL",
            multiplicity_success_only_reporting=False,
            multiplicity_sealed_test_used_for_selection=False,
            unexecutable_reason_count=0,
            lifecycle_events=[
                *default_local_mock_lifecycle_events()[:-1],
                VirtualExecutionEvent(
                    event_type=VirtualExecutionEventType.RECONCILED_FLAT,
                    position_after=0.1,
                ),
            ],
        ),
        gate_id="virtual-gate-003",
        evaluated_at="2026-07-01T05:54:00Z",
    )

    assert duplicate.gate_state == "BLOCKED_BY_VIRTUAL_LIFECYCLE"
    assert "duplicate_submit_detected" in duplicate.blocker_codes
    assert unknown.gate_state == "BLOCKED_BY_VIRTUAL_LIFECYCLE"
    assert "unknown_lifecycle_state" in unknown.blocker_codes
    assert mismatch.gate_state == "BLOCKED_BY_VIRTUAL_LIFECYCLE"
    assert "flat_reconciliation_mismatch" in mismatch.blocker_codes


def test_virtual_execution_gate_schema_validates_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_p5_artifacts(tmp_path)
    result = build_and_write_virtual_execution_gate(
        candidate_set_path=paths["candidate_set"],
        factory_summary_path=paths["factory_summary"],
        multiplicity_account_path=paths["multiplicity"],
        backtest_kill_gate_path=paths["kill_gate"],
        candidate_id="idea-cand-001",
        out_dir=tmp_path / "virtual_gate",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/virtual_execution_gate.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.gate.model_dump(mode="json"))


def test_virtual_execution_gate_cli_writes_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_p5_artifacts(tmp_path)
    out_dir = tmp_path / "virtual_gate_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-virtual-gate-run",
            "--candidate-set",
            str(paths["candidate_set"]),
            "--factory-summary",
            str(paths["factory_summary"]),
            "--multiplicity-account",
            str(paths["multiplicity"]),
            "--backtest-kill-gate",
            str(paths["kill_gate"]),
            "--candidate-id",
            "idea-cand-001",
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "status=pass" in result.stdout
    assert "gate_state=LOCAL_MOCK_VERIFIED" in result.stdout
    assert (out_dir / "virtual_execution_gate.json").exists()
