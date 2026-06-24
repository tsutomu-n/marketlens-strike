from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.strategy_authoring_pack import register_strategy_authoring_pack_commands
from support.cli import normalized_stdout


def test_strategy_authoring_pack_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_strategy_authoring_pack_commands(app)

    result = CliRunner().invoke(app, ["strategy-backtest-pack", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "strategy-backtest-pack" in stdout
    assert "--benchmark-series-path" in stdout
