from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.strategy_authoring_frameworks import (
    register_strategy_authoring_framework_commands,
)
from support.cli import normalized_stdout


def test_strategy_authoring_framework_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_strategy_authoring_framework_commands(app)

    result = CliRunner().invoke(app, ["strategy-backtest-framework-run", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "strategy-backtest-framework-run" in stdout
    assert "--framework" in stdout
