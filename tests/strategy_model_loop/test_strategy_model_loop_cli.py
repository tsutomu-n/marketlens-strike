from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_model_loop import _training_data, _trials


runner = CliRunner()


def test_strategy_model_run_record_help() -> None:
    result = runner.invoke(app, ["strategy-model-run-record", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--training-data" in stdout
    assert "--trial-json" in stdout
    assert "--output-route" in stdout


def test_strategy_model_run_record_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    args = [
        "strategy-model-run-record",
        "--strategy-id",
        "ndx-breakout-001",
        "--training-data",
        str(_training_data(tmp_path)),
        "--label-definition",
        "next_10_bar_return",
        "--split",
        "train=2024,validation=2025,holdout=2026",
        "--search-space-json",
        json.dumps({"lookback": [20, 80]}),
        "--best-trial-id",
        "trial-001",
        "--holdout-result-json",
        json.dumps({"return": 0.03}),
        "--limitation",
        "small holdout window",
        "--out",
        str(tmp_path / "data/strategy_model_loop/ndx-breakout-001"),
    ]
    for trial in _trials():
        args.extend(["--trial-json", json.dumps(trial)])

    result = runner.invoke(app, args)

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "trial_count=2" in result.stdout
    assert "failed_count=1" in result.stdout
    assert "success_only_reporting=false" in result.stdout
