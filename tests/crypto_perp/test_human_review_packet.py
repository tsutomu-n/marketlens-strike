from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.human_review_packet import (
    EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES,
    build_human_review_packet,
)
from .human_review_packet_fixtures import (
    _backtest,
    _bias_guard,
    _data_availability,
    _decide_state,
    _decision,
    _gate,
    _kill,
    _leaderboard,
    _packet,
    _packet_cli_args,
    _rolling_stability,
    _schema,
    _selection_manifest,
    _stress,
    _tournament_rows,
    _write_ready_cli_inputs,
)


runner = CliRunner()


def test_human_review_packet_ready_schema_valid() -> None:
    payload = _packet()

    assert payload["packet_decision"] == "BLOCKED_BY_PBO"
    assert payload["next_action"] == "FIX_REVIEW_PACKET_BLOCKERS"
    assert payload["current_evidence"]["pbo_computed"] is False
    assert payload["current_evidence"]["pbo_evidence_verified"] is False
    assert payload["required_human_review"] is True
    assert payload["permits_paper_order"] is False
    assert payload["actual_cash_used"] is False
    assert payload["profit_proven"] is False
    assert "BOOKS_SOURCE_MISSING" in payload["known_gaps"]
    Draft202012Validator(_schema("crypto_perp_human_review_packet.v1.schema.json")).validate(
        payload
    )


def test_candidate_not_hold_blocks_packet_even_when_downstream_claims_hold() -> None:
    decision = _decision()
    decision["decision"] = "BACKTEST_REJECT"

    packet_decision, reason_codes = _decide_state(candidate_decision="BACKTEST_REJECT")

    assert packet_decision == "BLOCKED_BY_CANDIDATE"
    assert "BACKTEST_CANDIDATE_NOT_HOLD" in reason_codes


def test_explicit_artifact_lineage_violation_blocks_packet() -> None:
    payload = build_human_review_packet(
        selection_manifest=_selection_manifest(),
        decision=_decision(),
        tournament_rows=_tournament_rows(),
        bias_guard=_bias_guard(),
        data_availability=_data_availability(),
        signal_rows=[],
        backtest=_backtest(),
        stress=_stress(),
        rolling_stability=_rolling_stability(),
        gate=_gate(),
        kill_report=_kill(),
        leaderboard=_leaderboard(),
        created_at="2026-07-09T00:00:00Z",
        input_artifacts={},
        source_refs=[],
        lineage_violations=["GATE_DECISION_SOURCE_REF_MISMATCH"],
    )

    assert payload["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "GATE_DECISION_SOURCE_REF_MISMATCH" in payload["reason_codes"]


def test_nested_boundary_violation_in_any_input_blocks_packet() -> None:
    decision = _decision()
    decision["boundary"] = {"permits_live_order": True}

    payload = _packet(decision=decision)

    assert payload["packet_decision"] == "BLOCKED_BY_BOUNDARY_VIOLATION"


def test_human_review_packet_v1_schema_keeps_old_current_evidence_compatible() -> None:
    payload = _packet()
    for key in (
        "artifact_lineage_status",
        "bias_guard_status",
        "bias_guard_artifact_id",
        "bias_guard_warning_codes",
        "profit_robustness",
    ):
        payload["current_evidence"].pop(key, None)

    Draft202012Validator(_schema("crypto_perp_human_review_packet.v1.schema.json")).validate(
        payload
    )


def test_gate_not_hold_blocks_packet() -> None:
    packet_decision, reason_codes = _decide_state(
        gate_decision="NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    )

    assert packet_decision == "BLOCKED_BY_GATE"
    assert reason_codes == ["NO_CASH_GATE_NOT_HOLD"]


def test_blocked_bias_guard_wins_over_incorrect_downstream_holds() -> None:
    decision = _decision()
    decision["summary"]["bias_guard_status"] = "BLOCKED"
    decision["summary"]["bias_guard_stop_reasons"] = ["BIAS_GUARD_FAILED_stress_cash_non_negative"]

    payload = _packet(
        decision=decision,
        bias_guard=_bias_guard(
            guard_status="BLOCKED",
            stop_reasons=["BIAS_GUARD_FAILED_stress_cash_non_negative"],
        ),
    )

    assert payload["packet_decision"] == "BLOCKED_BY_BIAS_GUARD"
    assert payload["next_action"] == "FIX_REVIEW_PACKET_BLOCKERS"
    assert payload["current_evidence"]["bias_guard_status"] == "BLOCKED"
    assert "BIAS_GUARD_FAILED_stress_cash_non_negative" in payload["reason_codes"]


def test_bias_guard_warning_remains_visible_in_ready_packet() -> None:
    warning = "BIAS_GUARD_WARNING_stress_cash_non_negative"
    decision = _decision()
    decision["summary"]["bias_guard_warning_codes"] = [warning]
    gate = _gate(known_gaps=[warning, "TRADES_SOURCE_MISSING"])

    payload = _packet(
        decision=decision,
        bias_guard=_bias_guard(known_gaps=[warning]),
        gate=gate,
    )

    assert payload["packet_decision"] == "BLOCKED_BY_PBO"
    assert payload["current_evidence"]["bias_guard_warning_codes"] == [warning]
    assert warning in payload["known_gaps"]
    assert any("bias guard warning" in question.lower() for question in payload["review_questions"])
    Draft202012Validator(_schema("crypto_perp_human_review_packet.v1.schema.json")).validate(
        payload
    )


@pytest.mark.parametrize("status", [None, "NOT_RUN", "UNKNOWN"])
def test_missing_or_unknown_bias_guard_never_becomes_ready(status: str | None) -> None:
    decision = _decision()
    if status is None:
        decision["summary"].pop("bias_guard_status")
        guard = _bias_guard()
        guard.pop("guard_status")
    else:
        decision["summary"]["bias_guard_status"] = status
        guard = _bias_guard(guard_status=status)

    payload = _packet(decision=decision, bias_guard=guard)

    assert payload["packet_decision"] == "BLOCKED_BY_BIAS_GUARD"


def test_non_goal_flags_boundary_violation_blocks_packet() -> None:
    decision = _decision()
    decision["non_goal_flags"] = {"exchange_write_used": True}

    payload = _packet(decision=decision)

    assert payload["packet_decision"] == "BLOCKED_BY_BOUNDARY_VIOLATION"


@pytest.mark.parametrize("pbo_status", [None, "NOT_ESTIMABLE", "INPUT_THRESHOLD_MET", "UNKNOWN"])
def test_pbo_must_be_computed_pass_for_ready(pbo_status: str | None) -> None:
    guard = _bias_guard()
    decision = _decision()
    gate = _gate()
    if pbo_status is None:
        guard.pop("pbo_status")
        decision["summary"].pop("pbo_status")
        gate["summary"].pop("pbo_status")
    else:
        guard["pbo_status"] = pbo_status
        decision["summary"]["pbo_status"] = pbo_status
        gate["summary"]["pbo_status"] = pbo_status

    payload = _packet(decision=decision, bias_guard=guard, gate=gate)

    assert payload["packet_decision"] == "BLOCKED_BY_PBO"


def test_secondary_candidate_blockers_reach_pbo_blocked_packet() -> None:
    decision = _decision()
    decision["decision"] = "BACKTEST_COLLECT_MORE_DATA"
    decision["reason_codes"] = ["PBO_NOT_COMPUTED", "POSITION_OVERLAP_NOT_ACCOUNTED"]
    decision["summary"]["pbo_status"] = "INPUT_THRESHOLD_MET"
    gate = _gate(
        gate_decision="NO_CASH_BACKTEST_COLLECT_MORE_DATA",
        reason_codes=["PBO_NOT_COMPUTED", "POSITION_OVERLAP_NOT_ACCOUNTED"],
    )

    payload = _packet(
        decision=decision,
        bias_guard=_bias_guard(pbo_status="INPUT_THRESHOLD_MET"),
        gate=gate,
    )

    assert payload["packet_decision"] == "BLOCKED_BY_PBO"
    assert "POSITION_OVERLAP_NOT_ACCOUNTED" in payload["reason_codes"]


def test_bias_guard_blocker_has_priority_over_candidate_reject() -> None:
    decision = _decision()
    decision["decision"] = "BACKTEST_REJECT"
    decision["summary"]["bias_guard_status"] = "BLOCKED"
    decision["summary"]["bias_guard_stop_reasons"] = ["BIAS_GUARD_FAILED_test"]

    payload = _packet(
        decision=decision,
        bias_guard=_bias_guard(guard_status="BLOCKED", stop_reasons=["BIAS_GUARD_FAILED_test"]),
    )

    assert payload["packet_decision"] == "BLOCKED_BY_BIAS_GUARD"
    assert "BIAS_GUARD_FAILED_test" in payload["reason_codes"]


def test_direct_builder_without_verified_lineage_never_becomes_ready() -> None:
    payload = build_human_review_packet(
        selection_manifest=_selection_manifest(),
        decision=_decision(),
        tournament_rows=_tournament_rows(),
        bias_guard=_bias_guard(),
        data_availability=_data_availability(),
        signal_rows=[],
        backtest=_backtest(),
        stress=_stress(),
        rolling_stability=_rolling_stability(),
        gate=_gate(),
        kill_report=_kill(),
        leaderboard=_leaderboard(),
        created_at="2026-07-09T00:00:00Z",
        input_artifacts={},
        source_refs=[],
    )

    assert payload["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "ARTIFACT_LINEAGE_NOT_VERIFIED" in payload["reason_codes"]


def test_kill_report_not_hold_blocks_packet() -> None:
    packet_decision, _ = _decide_state(kill_decision="KILL_AFTER_COST_NEGATIVE")

    assert packet_decision == "BLOCKED_BY_KILL_REPORT"


def test_leaderboard_not_hold_blocks_packet() -> None:
    packet_decision, _ = _decide_state(top_next_action="REVISE_SIGNAL")

    assert packet_decision == "BLOCKED_BY_LEADERBOARD"


def test_boundary_flag_blocks_packet() -> None:
    payload = _packet(kill_report=_kill(actual_cash_used=True))

    assert payload["packet_decision"] == "BLOCKED_BY_BOUNDARY_VIOLATION"
    assert payload["actual_cash_used"] is False


def test_human_review_packet_cli_blocks_missing_upstream_source_refs(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    for name in ("decision", "guard", "gate", "kill", "leaderboard"):
        payload = json.loads(paths[name].read_text(encoding="utf-8"))
        payload["source_refs"] = []
        paths[name].write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out-mixed"

    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0
    assert "packet_decision=BLOCKED_BY_ARTIFACT_LINEAGE" in result.stdout


def test_human_review_packet_cli_writes_artifacts(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    out = tmp_path / "out"

    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    assert "packet_decision=BLOCKED_BY_PBO" in result.stdout
    assert "permits_paper_order=false" in result.stdout
    assert (out / "human_review_packet.json").exists()
    assert (out / "human_review_packet.md").exists()


def test_human_review_packet_cli_blocks_overwritten_pack_component(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    backtest = json.loads(paths["backtest"].read_text(encoding="utf-8"))
    backtest["summary"]["total_result_usd"] = "999"
    paths["backtest"].write_text(json.dumps(backtest), encoding="utf-8")
    out = tmp_path / "out-overwritten"

    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert payload["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "DECISION_BACKTEST_RESULT_JSON_REF_MISMATCH" in payload["reason_codes"]


def test_human_review_packet_cli_blocks_wrong_input_schema(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    rows = json.loads(paths["rows"].read_text(encoding="utf-8"))
    rows["schema_version"] = "wrong-schema"
    paths["rows"].write_text(json.dumps(rows), encoding="utf-8")
    out = tmp_path / "out-schema"

    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert payload["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "TOURNAMENT_ROWS_SCHEMA_VERSION_MISMATCH" in payload["reason_codes"]


def test_builder_requires_exactly_twelve_named_input_artifacts() -> None:
    expected = {name: f"{name}.json" for name in EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES}
    missing = dict(expected)
    missing.pop("bias_guard")
    missing_payload = _packet(input_artifacts=missing)
    assert missing_payload["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "HUMAN_REVIEW_INPUT_MISSING_BIAS_GUARD" in missing_payload["reason_codes"]

    unexpected = {**expected, "forged_pbo": "forged.json"}
    unexpected_payload = _packet(input_artifacts=unexpected)
    assert unexpected_payload["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "HUMAN_REVIEW_INPUT_UNEXPECTED_FORGED_PBO" in unexpected_payload["reason_codes"]

    exact_payload = _packet(input_artifacts=expected)
    assert exact_payload["summary"]["review_input_count"] == 12
    assert [row["name"] for row in exact_payload["review_inputs"]] == list(
        EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES
    )


def test_builder_has_no_public_lineage_verified_boolean_escape_hatch() -> None:
    import inspect

    parameters = inspect.signature(build_human_review_packet).parameters
    assert "lineage_verified" not in parameters
    payload = _packet(_lineage_token=None)
    assert payload["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "ARTIFACT_LINEAGE_NOT_VERIFIED" in payload["reason_codes"]


def test_computed_pass_string_without_dedicated_evidence_never_becomes_ready() -> None:
    payload = _packet()

    assert payload["packet_decision"] == "BLOCKED_BY_PBO"
    assert "PBO_COMPUTATION_EVIDENCE_MISSING" in payload["reason_codes"]
    assert payload["current_evidence"]["pbo_status"] == "COMPUTED_PASS"
    assert payload["current_evidence"]["pbo_computed"] is False
    assert payload["current_evidence"]["pbo_evidence_verified"] is False


def test_packet_schema_keeps_pre_input_contract_v1_artifacts_readable() -> None:
    payload = _packet()
    payload.pop("input_contract_version")
    legacy_names = list(payload["input_artifacts"])[:7]
    payload["input_artifacts"] = {name: payload["input_artifacts"][name] for name in legacy_names}
    payload["review_inputs"] = payload["review_inputs"][:7]
    payload["summary"]["review_input_count"] = 7

    Draft202012Validator(_schema("crypto_perp_human_review_packet.v1.schema.json")).validate(
        payload
    )


def test_v2_packet_schema_rejects_duplicate_review_input_names() -> None:
    payload = _packet()
    payload["review_inputs"] = [payload["review_inputs"][0]] * 12

    errors = list(
        Draft202012Validator(_schema("crypto_perp_human_review_packet.v1.schema.json")).iter_errors(
            payload
        )
    )
    assert errors


def test_v2_packet_schema_rejects_review_input_count_mismatch() -> None:
    payload = _packet()
    payload["summary"]["review_input_count"] = 7

    errors = list(
        Draft202012Validator(_schema("crypto_perp_human_review_packet.v1.schema.json")).iter_errors(
            payload
        )
    )
    assert errors
