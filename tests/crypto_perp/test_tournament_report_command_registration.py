from __future__ import annotations

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_tournament_report import (
    register_crypto_perp_tournament_report_commands,
)
from support.cli import normalized_stdout


def test_crypto_perp_tournament_report_command_registers_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_tournament_report_commands(app)

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "crypto-perp-tournament-report" in stdout


def test_crypto_perp_tournament_report_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_tournament_report_commands(app)

    report_command = get_command(app)
    option_names = {
        option
        for parameter in report_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--rows" in option_names
    assert "--out" in option_names
    assert "--report-id" in option_names
    assert "--min-events" in option_names
    assert "--known-gap" in option_names
