from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout
from .test_strategy_input_feedback import _runtime_observation, _source_contract


runner = CliRunner()


def test_strategy_input_feedback_commands_help() -> None:
    proposal_result = runner.invoke(app, ["strategy-input-feedback-proposal-build", "--help"])
    proposal_stdout = normalized_stdout(proposal_result)
    assert proposal_result.exit_code == 0
    assert "--runtime-observat" in proposal_stdout
    assert "--learning-event" in proposal_stdout
    assert "--source-contract" in proposal_stdout

    review_result = runner.invoke(app, ["strategy-input-feedback-proposal-review", "--help"])
    review_stdout = normalized_stdout(review_result)
    assert review_result.exit_code == 0
    assert "--approved-chan" in review_stdout
    assert "--decision" in review_stdout


def test_strategy_input_feedback_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runtime = _runtime_observation(tmp_path)
    contract = _source_contract(tmp_path)

    proposal_result = runner.invoke(
        app,
        [
            "strategy-input-feedback-proposal-build",
            "--strategy-id",
            "ndx-breakout-001",
            "--runtime-observation",
            str(runtime),
            "--source-contract",
            str(contract),
            "--out",
            str(tmp_path / "data/strategy_input_feedback"),
            "--proposal-id",
            "proposal-cli",
        ],
    )

    assert proposal_result.exit_code == 0, proposal_result.stdout
    assert "proposal_status=READY_FOR_HUMAN_REVIEW" in proposal_result.stdout
    assert "direct_contract_edit_allowed=false" in proposal_result.stdout

    review_result = runner.invoke(
        app,
        [
            "strategy-input-feedback-proposal-review",
            "--proposal",
            str(tmp_path / "data/strategy_input_feedback/ndx-breakout-001/proposal-cli.json"),
            "--decision",
            "APPROVE_FOR_MANUAL_CONTRACT_UPDATE",
            "--reviewer",
            "operator-a",
            "--rationale",
            "Approved for manual contract update input only.",
            "--approved-change-id",
            "runtime-001",
        ],
    )

    assert review_result.exit_code == 0, review_result.stdout
    assert "decision=APPROVE_FOR_MANUAL_CONTRACT_UPDATE" in review_result.stdout
    assert "manual_contract_update_input_allowed=true" in review_result.stdout
    assert "direct_contract_edit_allowed=false" in review_result.stdout


def test_strategy_input_feedback_cli_rejects_empty_sources(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-input-feedback-proposal-build",
            "--strategy-id",
            "ndx-breakout-001",
            "--out",
            str(tmp_path / "data/strategy_input_feedback"),
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "at least one" in result.stdout
