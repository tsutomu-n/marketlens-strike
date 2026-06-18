from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_live_observation import _audit_bundle, _micro_live_plan, _report


runner = CliRunner()


def test_strategy_live_observation_help() -> None:
    result = runner.invoke(app, ["strategy-live-observation-ingest", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--audit-bundle" in stdout
    assert "--micro-live-plan" in stdout
    assert "--observation-id" in stdout


def test_strategy_live_observation_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-live-observation-ingest",
            "--strategy-id",
            "ndx-breakout-001",
            "--audit-bundle",
            str(_audit_bundle(tmp_path)),
            "--report",
            str(_report(tmp_path)),
            "--micro-live-plan",
            str(_micro_live_plan(tmp_path)),
            "--out",
            str(tmp_path / "data/strategy_live_observations"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "ingest_status=LIVE_OBSERVATION_INGESTED" in result.stdout
    assert "strategy_id=ndx-breakout-001" in result.stdout
