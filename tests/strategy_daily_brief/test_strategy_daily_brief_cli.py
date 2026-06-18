from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_daily_brief import _write_fixtures


runner = CliRunner()


def test_strategy_daily_brief_help() -> None:
    result = runner.invoke(app, ["strategy-daily-brief", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--data-dir" in stdout
    assert "--out" in stdout


def test_strategy_daily_brief_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    _write_fixtures(data_dir)

    result = runner.invoke(
        app,
        [
            "strategy-daily-brief",
            "--data-dir",
            str(data_dir),
            "--out",
            str(tmp_path / "data/reports/strategy_daily_brief"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "scanned_json_count=10" in result.stdout
    assert "boundary_violation_count=1" in result.stdout
