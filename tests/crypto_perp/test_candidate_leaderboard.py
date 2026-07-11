from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.candidate_leaderboard import build_candidate_leaderboard


ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _decision() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_candidate_pack.v1",
        "artifact_id": "decision-artifact",
        "pack_id": "pack-1",
        "summary": {"pbo_status": "ESTIMATED"},
        "evidence_grade_summary": {
            "event_count": 30,
            "critical_missing_count": 0,
            "source_missing_counts": {"books": 30, "trades": 30, "replay": 30},
        },
    }


def _backtest(total: str = "10") -> dict:
    return {
        "schema_version": "crypto_perp_backtest_result.v1",
        "summary": {
            "event_count": 30,
            "executed_trade_count": 10,
            "total_result_usd": total,
            "win_rate": "1",
            "max_drawdown_usd": "-1",
        },
    }


def _stress(total: str = "8") -> dict:
    return {
        "schema_version": "crypto_perp_backtest_stress_result.v1",
        "summary": {"total_result_usd": total},
    }


def _kill(decision: str) -> dict:
    return {
        "schema_version": "crypto_perp_no_trade_kill_report.v1",
        "kill_decision": decision,
        "reason_codes": [decision],
        "known_gaps": ["LOCAL_SIMULATION_ONLY"],
        "cost_adjusted_delta_vs_no_trade": "10",
        "stress_delta_vs_no_trade": "8",
        "largest_loss_concentration": "0.1",
        "largest_win_concentration": "0.1",
    }


def _gate(decision: str = "NO_CASH_BACKTEST_HOLD") -> dict:
    return {
        "schema_version": "crypto_perp_no_cash_backtest_gate.v1",
        "gate_decision": decision,
        "known_gaps": ["BOOKS_SOURCE_MISSING"],
        "summary": {"rolling_stability_status": "complete", "event_count": 30},
    }


def _leaderboard(kill_decision: str) -> dict:
    return build_candidate_leaderboard(
        decision=_decision(),
        backtest=_backtest(),
        stress=_stress(),
        kill_report=_kill(kill_decision),
        gate=_gate(),
        signal_rows=[{"symbol": "BTCUSDT", "selected_action": "CONTINUATION_LONG"}],
        created_at="2026-07-09T00:00:00Z",
        input_artifacts={
            "decision": "decision.json",
            "backtest": "backtest.json",
            "stress": "stress.json",
            "kill_report": "kill.json",
            "gate": "gate.json",
        },
        source_refs=[],
    )


def test_leaderboard_hold_schema_valid() -> None:
    payload = _leaderboard("HOLD_FOR_LEADERBOARD")

    assert payload["rows"][0]["next_action"] == "HOLD_FOR_HUMAN_REVIEW"
    assert payload["rows"][0]["rank"] == 1
    assert payload["permits_paper_order"] is False
    Draft202012Validator(_schema("crypto_perp_candidate_leaderboard.v1.schema.json")).validate(
        payload
    )


def test_kill_decisions_map_to_kill() -> None:
    payload = _leaderboard("KILL_AFTER_COST_NEGATIVE")

    assert payload["rows"][0]["next_action"] == "KILL"


def test_revise_decision_maps_to_revise_signal() -> None:
    payload = _leaderboard("REVISE_SOURCE_OR_SIGNAL")

    assert payload["rows"][0]["next_action"] == "REVISE_SIGNAL"


def test_collect_decision_maps_to_collect_more_data() -> None:
    payload = _leaderboard("COLLECT_MORE_DATA")

    assert payload["rows"][0]["next_action"] == "COLLECT_MORE_DATA"


def test_gate_reject_overrides_incorrect_kill_report_hold() -> None:
    payload = build_candidate_leaderboard(
        decision=_decision(),
        backtest=_backtest(),
        stress=_stress(),
        kill_report=_kill("HOLD_FOR_LEADERBOARD"),
        gate=_gate("NO_CASH_BACKTEST_REJECT"),
        signal_rows=[{"symbol": "BTCUSDT", "selected_action": "CONTINUATION_LONG"}],
        created_at="2026-07-09T00:00:00Z",
        input_artifacts={},
        source_refs=[],
    )

    assert payload["rows"][0]["next_action"] == "KILL"
    assert "UPSTREAM_GATE_REJECTED" in payload["rows"][0]["reason_codes"]


def test_candidate_leaderboard_cli_writes_artifacts(tmp_path: Path) -> None:
    paths = {
        "decision": tmp_path / "decision.json",
        "backtest": tmp_path / "backtest.json",
        "stress": tmp_path / "stress.json",
        "kill": tmp_path / "kill.json",
        "gate": tmp_path / "gate.json",
        "signal": tmp_path / "signal_rows.jsonl",
    }
    paths["decision"].write_text(json.dumps(_decision()), encoding="utf-8")
    paths["backtest"].write_text(json.dumps(_backtest()), encoding="utf-8")
    paths["stress"].write_text(json.dumps(_stress()), encoding="utf-8")
    paths["kill"].write_text(json.dumps(_kill("HOLD_FOR_LEADERBOARD")), encoding="utf-8")
    paths["gate"].write_text(json.dumps(_gate()), encoding="utf-8")
    paths["signal"].write_text(
        json.dumps({"symbol": "BTCUSDT", "selected_action": "CONTINUATION_LONG"}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "crypto-perp-candidate-leaderboard",
            "--decision",
            str(paths["decision"]),
            "--backtest",
            str(paths["backtest"]),
            "--stress",
            str(paths["stress"]),
            "--kill-report",
            str(paths["kill"]),
            "--gate",
            str(paths["gate"]),
            "--signal-rows",
            str(paths["signal"]),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert "top_next_action=HOLD_FOR_HUMAN_REVIEW" in result.stdout
    assert (out / "candidate_leaderboard.json").exists()
    assert (out / "candidate_leaderboard.md").exists()
