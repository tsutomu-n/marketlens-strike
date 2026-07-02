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
