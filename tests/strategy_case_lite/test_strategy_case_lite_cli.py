from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_case_lite import (
    _drift_review,
    _live_observation,
    _micro_live_plan,
    _next_scale_plan,
    _scale_decision,
    _stage_decision,
    _backtest_result,
    _strategy_review_manifest,
)


runner = CliRunner()


def test_strategy_case_lite_update_help() -> None:
    result = runner.invoke(app, ["strategy-case-lite-update", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--strategy-id" in stdout
    assert "--stage-decision" in stdout
    assert "--drift-review" in stdout
    assert "--micro-live-plan" in stdout
    assert "--live-observation" in stdout
    assert "--scale-decision" in stdout
    assert "--next-scale-plan" in stdout
    assert "--artifact" in stdout


def test_strategy_case_lite_update_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-case-lite-update",
            "--strategy-id",
            "ndx-breakout-001",
            "--stage-decision",
            str(_stage_decision(tmp_path)),
            "--drift-review",
            str(_drift_review(tmp_path)),
            "--micro-live-plan",
            str(_micro_live_plan(tmp_path)),
            "--live-observation",
            str(_live_observation(tmp_path)),
            "--scale-decision",
            str(_scale_decision(tmp_path)),
            "--next-scale-plan",
            str(_next_scale_plan(tmp_path)),
            "--out",
            str(tmp_path / "data/strategy_cases"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "strategy_id=ndx-breakout-001" in result.stdout
    assert "artifact_count=6" in result.stdout


def test_strategy_case_lite_update_cli_accepts_generic_artifact_option(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-case-lite-update",
            "--strategy-id",
            "trend_pullback_user_v1",
            "--artifact",
            str(_backtest_result(tmp_path)),
            "--artifact",
            str(_strategy_review_manifest(tmp_path)),
            "--out",
            str(tmp_path / "data/strategy_cases"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "strategy_id=trend_pullback_user_v1" in result.stdout
    assert "latest_status=READY_FOR_HUMAN_REVIEW" in result.stdout
    assert "artifact_count=2" in result.stdout
