from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_edge_candidate_factory_build_help() -> None:
    result = runner.invoke(app, ["edge-candidate-factory-build", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--source-root" in stdout
    assert "--symbol" in stdout
    assert "--candidate-cap" in stdout
    assert "replace-exist" in stdout


def test_edge_candidate_backtest_kill_gate_help() -> None:
    result = runner.invoke(app, ["edge-candidate-backtest-kill-gate", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--candidate-id" in stdout
    assert "--family-id" in stdout
    assert "--metrics" in stdout


def test_edge_candidate_virtual_execution_gate_help() -> None:
    result = runner.invoke(app, ["edge-candidate-virtual-execution-gate", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--candidate-id" in stdout
    assert "--venue-id" in stdout
    assert "reconciliation" in stdout


def test_edge_candidate_risk_actual_cash_handoff_help() -> None:
    result = runner.invoke(app, ["edge-candidate-risk-actual-cash-handoff", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--candidate-id" in stdout
    assert "actual-cash" in stdout


def test_edge_candidate_factory_build_cli_writes_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "edge-candidate-factory-build",
            "--source-root",
            "data/prep/watchdeck",
            "--symbol",
            "BTCUSDT",
            "--product-type",
            "USDT-FUTURES",
            "--timeframe",
            "5m",
            "--family",
            "liquidation_exhaustion_reversal",
            "--family",
            "spread_widening_no_trade",
            "--candidate-cap",
            "1",
            "--out",
            "data/edge_candidate_factory/test-run",
            "--run-id",
            "edge-cli-001",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "credentials_used=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "production_exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "permits_live_order=false" in result.stdout
    assert "status=pass" in result.stdout
    assert "known_gap_count=" in result.stdout

    out_dir = tmp_path / "data/edge_candidate_factory/test-run"
    report_path = out_dir / "smart_candidate_prior_report.json"
    ledger_path = out_dir / "edge_candidate_search_ledger.jsonl"
    multiplicity_path = out_dir / "trial_multiplicity_account.json"
    rejections_path = out_dir / "candidate_rejections.jsonl"
    assert report_path.exists()
    assert (out_dir / "smart_candidate_prior_report.md").exists()
    assert ledger_path.exists()
    assert multiplicity_path.exists()
    assert rejections_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("smart_candidate_prior_report.v1.schema.json")).validate(report)
    assert report["candidate_count_total"] == 1
    assert report["boundary"]["permits_live_order"] is False
    assert report["generator_config"]["source_root"] == "data/prep/watchdeck"

    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert [row["row_kind"] for row in rows] == ["candidate", "cap_rejection"]

    rerun = runner.invoke(
        app,
        [
            "edge-candidate-factory-build",
            "--source-root",
            "data/prep/watchdeck",
            "--symbol",
            "BTCUSDT",
            "--family",
            "liquidation_exhaustion_reversal",
            "--out",
            "data/edge_candidate_factory/test-run",
            "--run-id",
            "edge-cli-001",
        ],
    )
    assert rerun.exit_code == 2
    assert "status=fail" in rerun.stdout


def test_edge_candidate_backtest_kill_gate_cli_writes_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    build = runner.invoke(
        app,
        [
            "edge-candidate-factory-build",
            "--source-root",
            "data/prep/watchdeck",
            "--symbol",
            "BTCUSDT",
            "--family",
            "liquidation_exhaustion_reversal",
            "--candidate-cap",
            "1",
            "--out",
            "data/edge_candidate_factory/test-run",
            "--run-id",
            "edge-cli-002",
        ],
    )
    assert build.exit_code == 0, build.stdout

    report_path = (
        tmp_path / "data/edge_candidate_factory/test-run/smart_candidate_prior_report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate_id = report["candidate_cards"][0]["candidate_id"]
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_backtest_baseline_comparison.v1",
                "summary": {
                    "event_count": 120,
                    "closed_trade_count": 80,
                    "after_cost_edge_over_no_trade_usd": 10.0,
                    "stress_edge_over_no_trade_usd": 4.0,
                    "largest_loss_usd": -100.0,
                    "profit_concentration": 0.25,
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "edge-candidate-backtest-kill-gate",
            "--candidate-id",
            candidate_id,
            "--family-id",
            "liquidation_exhaustion_reversal",
            "--multiplicity-account",
            "data/edge_candidate_factory/test-run/trial_multiplicity_account.json",
            "--metrics",
            str(metrics_path),
            "--out",
            "data/edge_candidate_factory/gates",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "status=research_only" in result.stdout
    gate_path = tmp_path / f"data/edge_candidate_factory/gates/{candidate_id}.json"
    assert gate_path.exists()
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("backtest_kill_gate.v1.schema.json")).validate(gate)
    assert gate["gate_status"] == "RESEARCH_ONLY"
    assert gate["boundary"]["paper_execution_allowed"] is False


def test_edge_candidate_virtual_execution_gate_cli_writes_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "edge-candidate-virtual-execution-gate",
            "--candidate-id",
            "edge-cand-001",
            "--venue-id",
            "bitget",
            "--out",
            "data/edge_candidate_factory/virtual_gates",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "production_exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "status=virtual_passed_execution_lifecycle" in result.stdout
    gate_path = tmp_path / "data/edge_candidate_factory/virtual_gates/edge-cand-001.json"
    assert gate_path.exists()
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("virtual_execution_gate.v1.schema.json")).validate(gate)
    assert gate["gate_status"] == "VIRTUAL_PASSED_EXECUTION_LIFECYCLE"
    assert gate["actual_cash"] is False
    assert gate["cash_metric_basis"] == "virtual_exchange"
    assert gate["production_exchange_write_used"] is False


def test_edge_candidate_risk_actual_cash_handoff_cli_blocks_without_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    inputs = {
        "candidate_report.json": {"schema_version": "smart_candidate_prior_report.v1"},
        "search_ledger.jsonl": {"schema_version": "edge_candidate_search_ledger.v1"},
        "multiplicity.json": {"schema_version": "trial_multiplicity_account.v1"},
        "backtest_gate.json": {"schema_version": "backtest_kill_gate.v1"},
        "virtual_gate.json": {"schema_version": "virtual_execution_gate.v1"},
    }
    for name, payload in inputs.items():
        (tmp_path / name).write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "edge-candidate-risk-actual-cash-handoff",
            "--candidate-id",
            "edge-cand-001",
            "--candidate-report",
            "candidate_report.json",
            "--search-ledger",
            "search_ledger.jsonl",
            "--multiplicity-account",
            "multiplicity.json",
            "--backtest-kill-gate",
            "backtest_gate.json",
            "--virtual-execution-gate",
            "virtual_gate.json",
            "--out",
            "data/edge_candidate_factory/handoff",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "status=blocked_needs_actual_cash_rows" in result.stdout
    assert "crypto-perp-actual-cash-report-gate" not in result.stdout
    handoff_path = tmp_path / "data/edge_candidate_factory/handoff/edge-cand-001.json"
    assert handoff_path.exists()
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    Draft202012Validator(
        _schema("edge_candidate_risk_actual_cash_handoff.v1.schema.json")
    ).validate(handoff)
    assert handoff["actual_cash_rows_ref"] is None
    assert handoff["virtual_or_backtest_used_as_actual_cash"] is False
