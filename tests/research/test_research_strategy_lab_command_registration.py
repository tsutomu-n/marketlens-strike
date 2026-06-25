from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.research_strategy_lab import register_research_strategy_lab_commands
from support.cli import normalized_stdout


def test_research_strategy_lab_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_strategy_lab_commands(app, recommended_read_order_fn=lambda _: [])

    result = CliRunner().invoke(app, ["evaluate-strategy-lab", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "evaluate-strategy-lab" in stdout
    assert "--rank-thresholds" in stdout


def test_research_strategy_lab_parent_delegates_promotion_commands() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_strategy_lab_commands(app, recommended_read_order_fn=lambda _: [])

    promotion_result = CliRunner().invoke(app, ["promotion-decision", "--help"])
    intent_result = CliRunner().invoke(app, ["build-paper-intent-preview", "--help"])
    promotion_stdout = normalized_stdout(promotion_result)
    intent_stdout = normalized_stdout(intent_result)

    assert promotion_result.exit_code == 0
    assert intent_result.exit_code == 0
    assert "promotion-decision" in promotion_stdout
    assert "build-paper-intent-preview" in intent_stdout


def test_research_strategy_lab_parent_delegates_candidate_pack_command() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_strategy_lab_commands(app, recommended_read_order_fn=lambda _: [])

    result = CliRunner().invoke(app, ["build-paper-candidate-pack", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "build-paper-candidate-pack" in stdout
    assert "--trial-ledger" in stdout
    assert "--trial-group-id" in stdout
