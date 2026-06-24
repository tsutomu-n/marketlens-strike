from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.research_strategy_lifecycle import (
    register_research_strategy_lifecycle_commands,
)
from support.cli import normalized_stdout


def test_research_strategy_lifecycle_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_strategy_lifecycle_commands(app)

    result = CliRunner().invoke(app, ["strategy-paper-observation-cycle", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "strategy-paper-observation-cycle" in stdout
    assert "--paper-notional-usd" in stdout
