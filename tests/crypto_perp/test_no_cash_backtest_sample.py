from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app


runner = CliRunner()


def test_no_cash_backtest_sample_cli_feeds_candidate_pack_and_gate(tmp_path: Path) -> None:
    data_dir = tmp_path / "data/crypto_perp"
    sample_out = data_dir / "000_no_cash_backtest_sample/latest"

    sample = runner.invoke(
        app,
        [
            "crypto-perp-no-cash-backtest-sample",
            "--data-dir",
            str(data_dir),
            "--out",
            str(sample_out),
        ],
    )

    assert sample.exit_code == 0, sample.stdout
    assert "network_attempted=false" in sample.stdout
    assert "credentialed_exchange_api_used=false" in sample.stdout
    assert "exchange_write_used=false" in sample.stdout
    assert "actual_cash_used=false" in sample.stdout
    assert "fixture_only=true" in sample.stdout
    assert "real_market_evidence_claimed=false" in sample.stdout
    assert "event_count=30" in sample.stdout
    assert "outcome_count=30" in sample.stdout
    manifest = json.loads((sample_out / "selection_manifest.json").read_text(encoding="utf-8"))
    assert manifest["known_gaps"] == [
        "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE",
        "LOCAL_SIMULATION_ONLY",
        "NOT_ACTUAL_CASH",
    ]
    assert all(value is False for value in manifest["non_goal_flags"].values())

    pack_out = tmp_path / "pack"
    pack = runner.invoke(
        app,
        [
            "crypto-perp-backtest-candidate-pack",
            "--data-dir",
            str(data_dir),
            "--out",
            str(pack_out),
        ],
    )

    assert pack.exit_code == 0, pack.stdout
    assert "decision=BACKTEST_CANDIDATE_HOLD" in pack.stdout
    decision = json.loads((pack_out / "decision.json").read_text(encoding="utf-8"))
    assert decision["event_count"] == 30
    assert decision["outcome_count"] == 30
    assert decision["summary"]["pbo_status"] == "ESTIMATED"
    assert decision["summary"]["rolling_stability"]["event_count"] == 30
    assert decision["evidence_grade_summary"]["critical_missing_count"] == 0
    assert decision["evidence_grade_summary"]["future_signal_source_count"] == 0
    assert decision["evidence_grade_summary"]["simulated_trade_count"] >= 10
    assert (
        "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE"
        in decision["evidence_grade_summary"]["known_limits"]
    )

    gate_out = tmp_path / "gate"
    gate = runner.invoke(
        app,
        [
            "crypto-perp-no-cash-backtest-gate",
            "--decision",
            str(pack_out / "decision.json"),
            "--data-availability",
            str(pack_out / "data_availability_ledger.json"),
            "--backtest",
            str(pack_out / "backtest_result.json"),
            "--stress",
            str(pack_out / "stress_result.json"),
            "--rolling-stability",
            str(pack_out / "rolling_stability_result.json"),
            "--out",
            str(gate_out),
        ],
    )

    assert gate.exit_code == 0, gate.stdout
    assert "gate_decision=NO_CASH_BACKTEST_HOLD" in gate.stdout
    artifact = json.loads((gate_out / "no_cash_backtest_gate.json").read_text(encoding="utf-8"))
    assert artifact["gate_decision"] == "NO_CASH_BACKTEST_HOLD"
    assert artifact["blockers"] == []
    assert artifact["summary"]["event_count"] == 30
    assert artifact["summary"]["executed_trade_count"] >= 10
    assert artifact["summary"]["pbo_status"] == "ESTIMATED"
    assert artifact["summary"]["paper_permission_granted"] is False
    assert artifact["summary"]["actual_cash_used"] is False
    assert "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE" in artifact["known_gaps"]
    assert "PAPER_PERMISSION_NOT_GRANTED" in artifact["known_gaps"]
