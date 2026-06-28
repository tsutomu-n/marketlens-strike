from __future__ import annotations

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_risk_taker_review import (
    register_crypto_perp_risk_taker_review_commands,
)


def test_crypto_perp_risk_taker_review_command_registers_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_risk_taker_review_commands(app)

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "crypto-perp-risk-taker-review" in result.stdout


def test_crypto_perp_risk_taker_review_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_risk_taker_review_commands(app)

    command = get_command(app)
    option_names = {
        option
        for parameter in command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--rows-v2" in option_names
    assert "--source-availability" in option_names
    assert "--bias-guard" in option_names
    assert "--operator-jurisdiction-status" in option_names
    assert "--source-freshness-status" in option_names
    assert "--venue-terms-checked-at" in option_names
    assert "--liquidation-buffer-bps" in option_names
    assert "--out" in option_names
