from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_workbench_viewer import _stage_decision, _unsafe_review


runner = CliRunner()


def test_strategy_workbench_viewer_help() -> None:
    result = runner.invoke(app, ["strategy-workbench-viewer-build", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--artifact" in stdout
    assert "--data-dir" in stdout
    assert "--out" in stdout


def test_strategy_workbench_viewer_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    stage = _stage_decision(tmp_path / "data/strategy_stage/stage.json")
    review = _unsafe_review(tmp_path / "data/strategy_reviews/review.md")

    result = runner.invoke(
        app,
        [
            "strategy-workbench-viewer-build",
            "--artifact",
            str(stage),
            "--artifact",
            str(review),
            "--out",
            str(tmp_path / "data/reports/strategy_workbench_viewer"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "artifact_count=2" in result.stdout
    assert (
        tmp_path / "data/reports/strategy_workbench_viewer/strategy_workbench_viewer.html"
    ).exists()
