from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from sis.strategy_stage.models import StageName
from sis.strategy_stage.service import build_stage_decision
from support.cli import normalized_stdout

from .test_strategy_paper_smoke_plan import (
    _write_operator_review,
    _write_policy,
    _write_required_sources,
)


runner = CliRunner()


def _stage_decision(tmp_path: Path) -> tuple[Path, Path]:
    policy_path = _write_policy(tmp_path)
    operator_review_path = _write_operator_review(tmp_path)
    result = build_stage_decision(
        strategy_id="ndx-breakout-001",
        stage=StageName.PAPER_SMOKE,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-paper-smoke",
        review_dir=operator_review_path.parent,
    )
    return policy_path, result.decision_path


def test_strategy_paper_smoke_plan_help() -> None:
    result = runner.invoke(app, ["strategy-paper-smoke-plan", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--stage-decisi" in stdout
    assert "--session-id" in stdout
    assert "--source-pack" in stdout


def test_strategy_paper_smoke_plan_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path, stage_decision_path = _stage_decision(tmp_path)
    sources = _write_required_sources(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-paper-smoke-plan",
            "--stage-decision",
            str(stage_decision_path),
            "--policy",
            str(policy_path),
            "--out",
            str(tmp_path / "data/strategy_paper_smoke/ndx-breakout-001"),
            "--data-dir",
            str(tmp_path / "data"),
            "--artifact-dir",
            str(tmp_path / "data/research/ndx"),
            "--reports-dir",
            str(tmp_path / "data/reports"),
            "--session-id",
            "smoke-001",
            "--backtest-acceptance-path",
            str(sources["backtest_acceptance"]),
            "--source-pack",
            str(sources["source_pack"]),
            "--promotion-decision",
            str(sources["promotion_decision"]),
            "--operator-promotion-path",
            str(sources["operator_promotion"]),
        ],
    )

    assert result.exit_code == 0
    assert "plan_status=READY_TO_RUN_SMOKE_CYCLE" in result.stdout
    assert "failed_condition_count=0" in result.stdout


def test_strategy_paper_smoke_plan_cli_missing_sources_exits_two(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path, stage_decision_path = _stage_decision(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-paper-smoke-plan",
            "--stage-decision",
            str(stage_decision_path),
            "--policy",
            str(policy_path),
            "--out",
            str(tmp_path / "data/strategy_paper_smoke/ndx-breakout-001"),
            "--data-dir",
            str(tmp_path / "data"),
            "--artifact-dir",
            str(tmp_path / "data/research/ndx"),
            "--reports-dir",
            str(tmp_path / "data/reports"),
            "--session-id",
            "smoke-001",
        ],
    )

    assert result.exit_code == 2
    assert "plan_status=NEEDS_SOURCE_ARTIFACTS" in result.stdout
