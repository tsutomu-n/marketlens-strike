from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout
from .test_strategy_drift_review import (
    _backtest_result,
    _runtime_observation,
)


runner = CliRunner()


def test_strategy_drift_review_help() -> None:
    result = runner.invoke(app, ["strategy-drift-review", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--backtest-result" in stdout
    assert "--runtime-obser" in stdout
    assert "--max-no-fill-rate" in stdout
    assert "--max-return-drift" in stdout


def test_strategy_drift_review_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-drift-review",
            "--backtest-result",
            str(_backtest_result(tmp_path)),
            "--runtime-observation",
            str(_runtime_observation(tmp_path)),
            "--out",
            str(tmp_path / "data/strategy_drift_reviews/ndx-breakout-001/smoke-001"),
        ],
    )

    assert result.exit_code == 0
    assert "review_status=READY_FOR_HUMAN_DRIFT_REVIEW" in result.stdout
    assert "recommended_action=HUMAN_REVIEW_REQUIRED" in result.stdout
