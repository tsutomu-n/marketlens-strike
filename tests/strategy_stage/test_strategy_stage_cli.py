from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_stage_service import _write_operator_review, _write_policy


runner = CliRunner()


def test_strategy_stage_policy_validate_help() -> None:
    result = runner.invoke(app, ["strategy-stage-policy-validate", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--policy" in stdout
    assert "--out" in stdout
    assert "--replace-existing" in stdout


def test_strategy_stage_decision_help() -> None:
    result = runner.invoke(app, ["strategy-stage-decision", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--strategy-id" in stdout
    assert "--stage" in stdout
    assert "--policy" in stdout
    assert "--review-dir" in stdout
    assert "strategy_paper" in stdout


def test_strategy_stage_policy_validate_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-stage-policy-validate",
            "--policy",
            str(policy_path),
            "--out",
            str(tmp_path / "data/strategy_stage_policies/default"),
        ],
    )

    assert result.exit_code == 0
    assert "validation_status=PASS" in result.stdout
    assert "policy_id=personal_default_v1" in result.stdout


def test_strategy_stage_decision_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)
    operator_review_path = _write_operator_review(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-stage-decision",
            "--strategy-id",
            "ndx-breakout-001",
            "--stage",
            "paper_smoke",
            "--policy",
            str(policy_path),
            "--review-dir",
            str(operator_review_path.parent),
            "--out",
            str(tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-paper-smoke"),
        ],
    )

    assert result.exit_code == 0
    assert "decision=READY_FOR_PAPER_SMOKE_PLAN" in result.stdout
    assert "failed_condition_count=0" in result.stdout


def test_strategy_stage_decision_cli_missing_evidence_exits_two(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-stage-decision",
            "--strategy-id",
            "ndx-breakout-001",
            "--stage",
            "paper_smoke",
            "--policy",
            str(policy_path),
            "--review-dir",
            str(tmp_path / "data/strategy_reviews/ndx-review-001"),
            "--out",
            str(tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-paper-smoke"),
        ],
    )

    assert result.exit_code == 2
    assert "decision=NEEDS_EVIDENCE" in result.stdout
