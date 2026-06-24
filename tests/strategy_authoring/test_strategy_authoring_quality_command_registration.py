from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.strategy_authoring_quality import (
    register_strategy_authoring_quality_commands,
)
from support.cli import normalized_stdout


def test_strategy_authoring_quality_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_strategy_authoring_quality_commands(app)

    result = CliRunner().invoke(app, ["strategy-backtest-benchmark-relative", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "strategy-backtest-benchmark-relative" in stdout
    assert "--benchmark-series-path" in stdout
