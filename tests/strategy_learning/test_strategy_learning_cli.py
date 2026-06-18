from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout
from .test_strategy_learning import _authoring_spec, _drift_review


runner = CliRunner()


def test_strategy_learning_commands_help() -> None:
    ledger_result = runner.invoke(app, ["strategy-learning-ledger-update", "--help"])
    ledger_stdout = normalized_stdout(ledger_result)
    assert ledger_result.exit_code == 0
    assert "--drift-review" in ledger_stdout
    assert "--learning-event" in ledger_stdout

    revision_result = runner.invoke(app, ["strategy-revision-request-build", "--help"])
    revision_stdout = normalized_stdout(revision_result)
    assert revision_result.exit_code == 0
    assert "--learning-ledger" in revision_stdout
    assert "--revision-request" in revision_stdout

    review_result = runner.invoke(app, ["strategy-revision-request-review", "--help"])
    review_stdout = normalized_stdout(review_result)
    assert review_result.exit_code == 0
    assert "--revision-requ" in review_stdout
    assert "--decision" in review_stdout

    handoff_result = runner.invoke(app, ["strategy-authoring-update-handoff", "--help"])
    handoff_stdout = normalized_stdout(handoff_result)
    assert handoff_result.exit_code == 0
    assert "--revision-requ" in handoff_stdout
    assert "--revision-review" in handoff_stdout
    assert "--authoring-spec" in handoff_stdout


def test_strategy_learning_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    drift_review = _drift_review(tmp_path)

    ledger_result = runner.invoke(
        app,
        [
            "strategy-learning-ledger-update",
            "--drift-review",
            str(drift_review),
            "--out",
            str(tmp_path / "data/strategy_learning"),
            "--learning-event-id",
            "learn-001",
        ],
    )

    assert ledger_result.exit_code == 0, ledger_result.stdout
    assert "recommended_action=revise_strategy" in ledger_result.stdout

    revision_result = runner.invoke(
        app,
        [
            "strategy-revision-request-build",
            "--strategy-id",
            "ndx-breakout-001",
            "--learning-ledger",
            str(tmp_path / "data/strategy_learning/ndx-breakout-001/learning_ledger.jsonl"),
            "--out",
            str(tmp_path / "data/strategy_learning/ndx-breakout-001/revision_requests"),
            "--revision-request-id",
            "revise-001",
        ],
    )

    assert revision_result.exit_code == 0, revision_result.stdout
    assert "request_status=READY_FOR_HUMAN_REVIEW" in revision_result.stdout
    assert "reason=no_fill_drift" in revision_result.stdout

    review_result = runner.invoke(
        app,
        [
            "strategy-revision-request-review",
            "--revision-request",
            str(
                tmp_path
                / "data/strategy_learning/ndx-breakout-001/revision_requests/revise-001.json"
            ),
            "--decision",
            "APPROVE_FOR_AUTHORING_UPDATE",
            "--reviewer",
            "operator-a",
            "--rationale",
            "Approved as input to human authoring update.",
        ],
    )

    assert review_result.exit_code == 0, review_result.stdout
    assert "decision=APPROVE_FOR_AUTHORING_UPDATE" in review_result.stdout
    assert "authoring_update_input_allowed=true" in review_result.stdout

    handoff_result = runner.invoke(
        app,
        [
            "strategy-authoring-update-handoff",
            "--revision-request",
            str(
                tmp_path
                / "data/strategy_learning/ndx-breakout-001/revision_requests/revise-001.json"
            ),
            "--revision-review",
            str(
                tmp_path
                / "data/strategy_learning/ndx-breakout-001/revision_requests/revise-001_review.json"
            ),
            "--authoring-spec",
            str(_authoring_spec(tmp_path)),
            "--out",
            str(tmp_path / "data/strategy_learning/ndx-breakout-001/authoring_update_handoffs"),
            "--handoff-id",
            "authoring-handoff-001",
        ],
    )

    assert handoff_result.exit_code == 0, handoff_result.stdout
    assert "handoff_status=READY_FOR_HUMAN_AUTHORING_UPDATE" in handoff_result.stdout
    assert "auto_applied=false" in handoff_result.stdout
