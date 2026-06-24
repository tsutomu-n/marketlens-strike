from __future__ import annotations

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_data_bundle import register_quote_data_bundle_commands
from support.cli import normalized_stdout


def test_quote_data_bundle_command_registers_standalone() -> None:
    app = typer.Typer()
    register_quote_data_bundle_commands(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "build-trade-xyz-data-bundle" in stdout


def test_quote_data_bundle_command_keeps_collection_options() -> None:
    app = typer.Typer()
    register_quote_data_bundle_commands(app)

    root_command = get_command(app)
    option_names = {
        option
        for parameter in root_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--collection-config" in option_names
    assert "--auto-funding-window" in option_names
    assert "--no-auto-funding-window" in option_names
    assert "--collect-signal-candles" in option_names
    assert "--skip-signal-candles" in option_names
    assert "--collect-real-market-reference" in option_names
    assert "--skip-real-market-reference" in option_names
    assert "--account-fee-user-address" in option_names
