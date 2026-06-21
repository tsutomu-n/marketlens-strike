from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_next_scale_plan import _micro_live_plan, _scale_decision


runner = CliRunner()


def test_strategy_next_scale_plan_help() -> None:
    result = runner.invoke(app, ["strategy-next-scale-plan", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--scale-decision" in stdout
    assert "--micro-live-plan" in stdout
    assert "Next maximum order" in stdout


def test_strategy_next_scale_plan_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-next-scale-plan",
            "--strategy-id",
            "ndx-breakout-001",
            "--scale-decision",
            str(_scale_decision(tmp_path)),
            "--micro-live-plan",
            str(_micro_live_plan(tmp_path)),
            "--next-max-order-notional-usd",
            "15",
            "--next-max-position-notional-usd",
            "30",
            "--next-max-daily-loss-usd",
            "4",
            "--next-max-total-loss-usd",
            "8",
            "--next-max-open-positions",
            "1",
            "--allowed-symbols",
            "NDX",
            "--session-window",
            "XNYS regular session",
            "--monitoring-owner",
            "operator",
            "--monitoring-cadence",
            "every 15 minutes while active",
            "--schedule-cancel-procedure",
            "cancel all orders before session close",
            "--kill-switch-procedure",
            "stop strategy and flatten through approved manual process",
            "--out",
            str(tmp_path / "data/strategy_next_scale_plans"),
        ],
    )

    assert result.exit_code == 0
    assert "status=needs_human_approval" in result.stdout
    assert "requires_explicit_approval=true" in result.stdout
    assert "permits_live_order=false" in result.stdout
    assert "status=pass" not in result.stdout
    assert "plan_status=READY_FOR_HUMAN_NEXT_SCALE_REVIEW" in result.stdout
    assert "strategy_id=ndx-breakout-001" in result.stdout


def test_strategy_next_scale_plan_cli_blocked_when_scale_decision_not_ready(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-next-scale-plan",
            "--strategy-id",
            "ndx-breakout-001",
            "--scale-decision",
            str(_scale_decision(tmp_path, status="NEEDS_REPAIR")),
            "--micro-live-plan",
            str(_micro_live_plan(tmp_path)),
            "--next-max-order-notional-usd",
            "15",
            "--next-max-position-notional-usd",
            "30",
            "--next-max-daily-loss-usd",
            "4",
            "--next-max-total-loss-usd",
            "8",
            "--next-max-open-positions",
            "1",
            "--allowed-symbols",
            "NDX",
            "--session-window",
            "XNYS regular session",
            "--monitoring-owner",
            "operator",
            "--monitoring-cadence",
            "every 15 minutes while active",
            "--schedule-cancel-procedure",
            "cancel all orders before session close",
            "--kill-switch-procedure",
            "stop strategy and flatten through approved manual process",
            "--out",
            str(tmp_path / "data/strategy_next_scale_plans"),
        ],
    )

    assert result.exit_code == 0
    assert "status=blocked" in result.stdout
    assert "status=needs_human_approval" not in result.stdout
    assert "requires_explicit_approval=true" not in result.stdout
    assert "requires_explicit_approval=false" in result.stdout
    assert "permits_live_order=false" in result.stdout
    assert "status=pass" not in result.stdout
    assert "plan_status=NEEDS_SCALE_DECISION" in result.stdout
    assert "strategy_id=ndx-breakout-001" in result.stdout
