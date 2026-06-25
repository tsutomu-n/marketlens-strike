from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.research_strategy_lab_promotion import (
    register_research_strategy_lab_promotion_commands,
)
from support.cli import normalized_stdout


def test_research_strategy_lab_promotion_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_strategy_lab_promotion_commands(app)

    promotion_result = CliRunner().invoke(app, ["promotion-decision", "--help"])
    promotion_stdout = normalized_stdout(promotion_result)
    intent_result = CliRunner().invoke(app, ["build-paper-intent-preview", "--help"])
    intent_stdout = normalized_stdout(intent_result)

    assert promotion_result.exit_code == 0, promotion_result.stdout
    assert "promotion-decision" in promotion_stdout
    assert "--decision" in promotion_stdout
    assert "--source-pack" in promotion_stdout

    assert intent_result.exit_code == 0, intent_result.stdout
    assert "build-paper-intent-preview" in intent_stdout
    assert "--source-pack" in intent_stdout
    assert "--promotion-decision" in intent_stdout
