from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout
from .test_strategy_case_index import _case_lite


runner = CliRunner()


def test_strategy_case_index_build_help() -> None:
    result = runner.invoke(app, ["strategy-case-index-build", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--case" in stdout
    assert "--data-dir" in stdout
    assert "--index-id" in stdout


def test_strategy_case_index_build_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    case = _case_lite(
        tmp_path,
        strategy_id="ndx-breakout-001",
        case_id="case-a",
        updated_at="2026-06-22T09:00:00Z",
        latest_status="READY_FOR_HUMAN_REVIEW",
    )

    result = runner.invoke(
        app,
        [
            "strategy-case-index-build",
            "--case",
            str(case),
            "--out",
            str(tmp_path / "data/strategy_case_index"),
            "--index-id",
            "index-cli",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "case_count=1" in result.stdout
    assert "strategy_count=1" in result.stdout
    assert "db_persistence_allowed=false" in result.stdout


def test_strategy_case_index_build_cli_fails_without_cases(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-case-index-build",
            "--data-dir",
            str(tmp_path / "data/strategy_cases"),
            "--out",
            str(tmp_path / "data/strategy_case_index"),
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "no strategy_case_lite" in result.stdout
