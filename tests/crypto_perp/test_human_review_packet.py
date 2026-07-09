from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.human_review_packet import build_human_review_packet


ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _selection_manifest() -> dict:
    return {
        "schema_version": "crypto_perp_real_market_no_cash_sample.v1",
        "source_coverage": {
            "ticker_available_count": 30,
            "funding_available_count": 30,
            "require_ticker_coverage": True,
        },
        "known_gaps": ["BOOKS_SOURCE_MISSING", "LOCAL_SIMULATION_ONLY"],
    }


def _decision() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_candidate_pack.v1",
        "artifact_id": "decision-artifact",
        "pack_id": "pack-1",
        "decision": "BACKTEST_CANDIDATE_HOLD",
        "event_count": 30,
        "outcome_count": 30,
        "summary": {"pbo_status": "ESTIMATED"},
        "evidence_grade_summary": {
            "strongest_evidence_level": "recomputed_minimal_simulated_estimate",
            "event_count": 30,
            "critical_missing_count": 0,
        },
    }


def _backtest() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_result.v1",
        "summary": {
            "event_count": 30,
            "executed_trade_count": 13,
            "total_result_usd": "2.4",
            "beats_no_trade": True,
        },
    }


def _stress() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_stress_result.v1",
        "summary": {"total_result_usd": "2.1", "beats_no_trade": True},
    }


def _gate(**overrides) -> dict:
    payload = {
        "schema_version": "crypto_perp_no_cash_backtest_gate.v1",
        "gate_decision": "NO_CASH_BACKTEST_HOLD",
        "summary": {
            "event_count": 30,
            "outcome_count": 30,
            "critical_missing_count": 0,
            "unknown_count": 0,
            "executed_trade_count": 13,
            "pbo_status": "ESTIMATED",
            "rolling_stability_status": "complete",
        },
        "known_gaps": ["TRADES_SOURCE_MISSING"],
        "paper_permission_granted": False,
        "permits_paper_order": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }
    payload.update(overrides)
    return payload


def _kill(**overrides) -> dict:
    payload = {
        "schema_version": "crypto_perp_no_trade_kill_report.v1",
        "kill_decision": "HOLD_FOR_LEADERBOARD",
        "reason_codes": ["NO_TRADE_KILL_REPORT_HOLD_FOR_LEADERBOARD"],
        "known_gaps": ["NOT_ACTUAL_CASH"],
        "paper_permission_granted": False,
        "permits_paper_order": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }
    payload.update(overrides)
    return payload


def _leaderboard(**overrides) -> dict:
    payload = {
        "schema_version": "crypto_perp_candidate_leaderboard.v1",
        "rows": [{"candidate_id": "candidate-1", "next_action": "HOLD_FOR_HUMAN_REVIEW"}],
        "summary": {"top_next_action": "HOLD_FOR_HUMAN_REVIEW"},
        "known_gaps": ["NOT_LIVE_READINESS"],
        "paper_permission_granted": False,
        "permits_paper_order": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }
    payload.update(overrides)
    return payload


def _packet(**overrides) -> dict:
    return build_human_review_packet(
        selection_manifest=overrides.pop("selection_manifest", _selection_manifest()),
        decision=overrides.pop("decision", _decision()),
        backtest=overrides.pop("backtest", _backtest()),
        stress=overrides.pop("stress", _stress()),
        gate=overrides.pop("gate", _gate()),
        kill_report=overrides.pop("kill_report", _kill()),
        leaderboard=overrides.pop("leaderboard", _leaderboard()),
        created_at="2026-07-09T00:00:00Z",
        input_artifacts={
            "selection_manifest": "selection_manifest.json",
            "decision": "decision.json",
            "backtest": "backtest.json",
            "stress": "stress.json",
            "gate": "gate.json",
            "kill_report": "kill.json",
            "leaderboard": "leaderboard.json",
        },
        source_refs=[],
    )


def test_human_review_packet_ready_schema_valid() -> None:
    payload = _packet()

    assert payload["packet_decision"] == "READY_FOR_HUMAN_REVIEW_PLANNING"
    assert payload["next_action"] == "HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLANNING"
    assert payload["required_human_review"] is True
    assert payload["permits_paper_order"] is False
    assert payload["actual_cash_used"] is False
    assert payload["profit_proven"] is False
    assert "BOOKS_SOURCE_MISSING" in payload["known_gaps"]
    Draft202012Validator(_schema("crypto_perp_human_review_packet.v1.schema.json")).validate(
        payload
    )


def test_gate_not_hold_blocks_packet() -> None:
    payload = _packet(gate=_gate(gate_decision="NO_CASH_BACKTEST_COLLECT_MORE_DATA"))

    assert payload["packet_decision"] == "BLOCKED_BY_GATE"
    assert payload["next_action"] == "FIX_REVIEW_PACKET_BLOCKERS"


def test_kill_report_not_hold_blocks_packet() -> None:
    payload = _packet(kill_report=_kill(kill_decision="KILL_AFTER_COST_NEGATIVE"))

    assert payload["packet_decision"] == "BLOCKED_BY_KILL_REPORT"


def test_leaderboard_not_hold_blocks_packet() -> None:
    payload = _packet(
        leaderboard=_leaderboard(
            rows=[{"candidate_id": "candidate-1", "next_action": "REVISE_SIGNAL"}]
        )
    )

    assert payload["packet_decision"] == "BLOCKED_BY_LEADERBOARD"


def test_boundary_flag_blocks_packet() -> None:
    payload = _packet(kill_report=_kill(actual_cash_used=True))

    assert payload["packet_decision"] == "BLOCKED_BY_BOUNDARY_VIOLATION"
    assert payload["actual_cash_used"] is False


def test_human_review_packet_cli_writes_artifacts(tmp_path: Path) -> None:
    paths = {
        "selection": tmp_path / "selection_manifest.json",
        "decision": tmp_path / "decision.json",
        "backtest": tmp_path / "backtest.json",
        "stress": tmp_path / "stress.json",
        "gate": tmp_path / "gate.json",
        "kill": tmp_path / "kill.json",
        "leaderboard": tmp_path / "leaderboard.json",
    }
    paths["selection"].write_text(json.dumps(_selection_manifest()), encoding="utf-8")
    paths["decision"].write_text(json.dumps(_decision()), encoding="utf-8")
    paths["backtest"].write_text(json.dumps(_backtest()), encoding="utf-8")
    paths["stress"].write_text(json.dumps(_stress()), encoding="utf-8")
    paths["gate"].write_text(json.dumps(_gate()), encoding="utf-8")
    paths["kill"].write_text(json.dumps(_kill()), encoding="utf-8")
    paths["leaderboard"].write_text(json.dumps(_leaderboard()), encoding="utf-8")
    out = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "crypto-perp-human-review-packet",
            "--selection-manifest",
            str(paths["selection"]),
            "--decision",
            str(paths["decision"]),
            "--backtest",
            str(paths["backtest"]),
            "--stress",
            str(paths["stress"]),
            "--gate",
            str(paths["gate"]),
            "--kill-report",
            str(paths["kill"]),
            "--leaderboard",
            str(paths["leaderboard"]),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert "packet_decision=READY_FOR_HUMAN_REVIEW_PLANNING" in result.stdout
    assert "permits_paper_order=false" in result.stdout
    assert (out / "human_review_packet.json").exists()
    assert (out / "human_review_packet.md").exists()
