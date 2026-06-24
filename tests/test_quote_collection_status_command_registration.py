from __future__ import annotations

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_collection_status import register_quote_collection_status_commands
from support.cli import normalized_stdout


def test_quote_collection_status_command_registers_standalone() -> None:
    app = typer.Typer()
    register_quote_collection_status_commands(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "trade-xyz-collection-status" in stdout


def test_quote_collection_status_command_keeps_safety_options() -> None:
    app = typer.Typer()
    register_quote_collection_status_commands(app)

    root_command = get_command(app)
    option_names = {
        option
        for parameter in root_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--refresh-coverage" in option_names
    assert "--no-refresh-coverage" in option_names
    assert "--refresh-readiness" in option_names
    assert "--no-refresh-readiness" in option_names
    assert "--allow-known-gaps" in option_names
    assert "--strict" in option_names
    assert "--fail-on-not-ready" in option_names
    assert "--fail-on-stale" in option_names
    assert "--fail-on-lock-stale" in option_names
    assert "--fail-on-progress-warning" in option_names
    assert "--fail-on-archive-preflight" in option_names
    assert "--fail-on-account-fee-missing" in option_names
