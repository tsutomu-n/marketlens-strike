from __future__ import annotations

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_reference import register_quote_reference_commands
from support.cli import normalized_stdout


def test_quote_reference_commands_register_standalone() -> None:
    app = typer.Typer()
    register_quote_reference_commands(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "build-trade-xyz-quote-coverage" in stdout
    assert "build-trade-xyz-reference-data" in stdout
    assert "collect-trade-xyz-real-market-reference" in stdout
    assert "collect-trade-xyz-signal-candles" in stdout
    assert "collect-trade-xyz-account-fee" in stdout


def test_quote_reference_account_fee_keeps_user_address_option() -> None:
    app = typer.Typer()
    register_quote_reference_commands(app)

    root_command = get_command(app)
    account_fee_command = root_command.commands["collect-trade-xyz-account-fee"]
    option_names = {
        option
        for parameter in account_fee_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--user-address" in option_names
