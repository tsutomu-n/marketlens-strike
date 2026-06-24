from __future__ import annotations

import typer
import click
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_historical_archive import register_quote_historical_archive_commands
from support.cli import normalized_stdout


def test_historical_archive_quote_commands_register_standalone() -> None:
    app = typer.Typer()
    register_quote_historical_archive_commands(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "collect-trade-xyz-historical-l2-archive" in stdout
    assert "collect-trade-xyz-historical-asset-ctxs-archive" in stdout
    assert "normalize-trade-xyz-historical-archive-quotes" in stdout
    assert "plan-trade-xyz-historical-archive-bulk" in stdout
    assert "check-trade-xyz-historical-archive-preflight" in stdout
    assert "execute-trade-xyz-historical-archive-bulk" in stdout
    assert "normalize-trade-xyz-historical-archive-bulk" in stdout


def test_historical_archive_quote_command_help_keeps_requester_pays_ack() -> None:
    app = typer.Typer()
    register_quote_historical_archive_commands(app)

    root_command = get_command(app)
    archive_command = root_command.commands["execute-trade-xyz-historical-archive-bulk"]
    option_names = {
        option
        for parameter in archive_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--acknowledge-requester-pays" in option_names
    assert "--dry-run" in option_names
    assert "--execute" in option_names
