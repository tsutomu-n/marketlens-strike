from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_runtime_observation import _ledger_rows, _session_manifest, _write_jsonl


runner = CliRunner()


def test_strategy_runtime_observation_ingest_help() -> None:
    result = runner.invoke(app, ["strategy-runtime-observation-ingest", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--strategy-id" in stdout
    assert "--session-manif" in stdout
    assert "--source-stage" in stdout


def test_strategy_runtime_observation_ingest_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    ledger_path = _write_jsonl(
        tmp_path / "data/paper/observations/smoke-001/paper_observation_ledger.jsonl",
        _ledger_rows(),
    )
    session_manifest = _session_manifest(tmp_path, ledger_path=ledger_path)

    result = runner.invoke(
        app,
        [
            "strategy-runtime-observation-ingest",
            "--strategy-id",
            "ndx-breakout-001",
            "--session-manifest",
            str(session_manifest),
            "--out",
            str(tmp_path / "data/runtime_observations/ndx-breakout-001/smoke-001"),
            "--source-stage",
            "paper_smoke",
        ],
    )

    assert result.exit_code == 0
    assert "ingest_status=INGESTED" in result.stdout
    assert "ledger_entry_count=2" in result.stdout


def test_strategy_runtime_observation_ingest_cli_boundary_violation_exits_two(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rows = _ledger_rows()
    rows[0]["live_order_submitted"] = True
    ledger_path = _write_jsonl(
        tmp_path / "data/paper/observations/smoke-001/paper_observation_ledger.jsonl",
        rows,
    )
    session_manifest = _session_manifest(tmp_path, ledger_path=ledger_path)

    result = runner.invoke(
        app,
        [
            "strategy-runtime-observation-ingest",
            "--strategy-id",
            "ndx-breakout-001",
            "--session-manifest",
            str(session_manifest),
            "--out",
            str(tmp_path / "data/runtime_observations/ndx-breakout-001/smoke-001"),
        ],
    )

    assert result.exit_code == 2
    assert "ingest_status=BLOCKED_BOUNDARY_VIOLATION" in result.stdout
