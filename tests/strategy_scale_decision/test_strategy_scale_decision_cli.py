from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_scale_decision import _live_observation, _micro_live_plan


runner = CliRunner()


def test_strategy_scale_decision_help() -> None:
    result = runner.invoke(app, ["strategy-scale-decision", "--help"], terminal_width=160)
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--live-observation" in stdout
    assert "--micro-live-plan" in stdout
    assert "Require an actual" in stdout


def test_strategy_scale_decision_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-scale-decision",
            "--strategy-id",
            "ndx-breakout-001",
            "--live-observation",
            str(_live_observation(tmp_path)),
            "--micro-live-plan",
            str(_micro_live_plan(tmp_path)),
            "--out",
            str(tmp_path / "data/strategy_scale_decisions"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "decision_status=READY_FOR_HUMAN_SCALE_REVIEW" in result.stdout
    assert "recommended_action=PREPARE_NEXT_SCALE_PLAN" in result.stdout
