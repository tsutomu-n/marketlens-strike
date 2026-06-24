from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.strategy_authoring_portfolio import (
    register_strategy_authoring_portfolio_commands,
)
from support.cli import normalized_stdout


def test_strategy_authoring_portfolio_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_strategy_authoring_portfolio_commands(app)

    result = CliRunner().invoke(app, ["strategy-backtest-portfolio-compare", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "strategy-backtest-portfolio-compare" in stdout
    assert "--bundle-path" in stdout
