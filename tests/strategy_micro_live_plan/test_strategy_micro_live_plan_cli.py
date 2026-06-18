from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_micro_live_plan import _drift_review, _human_approval, _policy, _stage_decision


runner = CliRunner()


def test_strategy_micro_live_plan_help() -> None:
    result = runner.invoke(app, ["strategy-micro-live-plan", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--stage-decision" in stdout
    assert "--drift-review" in stdout
    assert "--max-order-notio" in stdout
    assert "--kill-switch-pro" in stdout


def test_strategy_micro_live_plan_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-micro-live-plan",
            "--strategy-id",
            "ndx-breakout-001",
            "--stage-decision",
            str(_stage_decision(tmp_path)),
            "--drift-review",
            str(_drift_review(tmp_path)),
            "--human-approval",
            str(_human_approval(tmp_path)),
            "--micro-live-policy",
            str(_policy(tmp_path)),
            "--max-order-notional-usd",
            "10",
            "--max-position-notional-usd",
            "20",
            "--max-daily-loss-usd",
            "5",
            "--max-total-loss-usd",
            "10",
            "--max-open-positions",
            "1",
            "--allowed-symbol",
            "SPY",
            "--session-window",
            "XNYS regular session only",
            "--monitoring-owner",
            "operator",
            "--monitoring-cadence",
            "watch every fill and every 5 minutes",
            "--schedule-cancel-procedure",
            "schedule cancel before submitting any canary order",
            "--kill-switch-procedure",
            "stop new orders and cancel open orders immediately",
            "--out",
            str(tmp_path / "data/strategy_micro_live_plans"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "plan_status=READY_FOR_HUMAN_MICRO_LIVE_REVIEW" in result.stdout
    assert "micro_live_execution_allowed=False" in result.stdout
