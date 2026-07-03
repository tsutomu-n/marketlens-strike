from __future__ import annotations

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_records import register_crypto_perp_record_commands
from support.cli import normalized_stdout


def test_crypto_perp_record_commands_register_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_record_commands(app)

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "crypto-perp-event-record" in stdout
    assert "crypto-perp-decision-record" in stdout
    assert "crypto-perp-outcome-record" in stdout


def test_crypto_perp_decision_record_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_record_commands(app)

    root_command = get_command(app)
    decision_command = root_command.commands["crypto-perp-decision-record"]
    option_names = {
        option
        for parameter in decision_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--event" in option_names
    assert "--action" in option_names
    assert "--out" in option_names
    assert "--actor-type" in option_names
    assert "--reason-code" in option_names
    assert "--review-seconds" in option_names


def test_crypto_perp_event_record_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_record_commands(app)

    root_command = get_command(app)
    event_command = root_command.commands["crypto-perp-event-record"]
    option_names = {
        option
        for parameter in event_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--input-csv" in option_names
    assert "--symbol" in option_names
    assert "--information-cutoff-at" in option_names
    assert "--out" in option_names
    assert "--contract" in option_names
    assert "--validation" in option_names
    assert "--lookback-minutes" in option_names


def test_crypto_perp_outcome_record_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_record_commands(app)

    root_command = get_command(app)
    outcome_command = root_command.commands["crypto-perp-outcome-record"]
    option_names = {
        option
        for parameter in outcome_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--event" in option_names
    assert "--event-id" in option_names
    assert "--horizon-minutes" in option_names
    assert "--reference-price" in option_names
    assert "--settled-at" in option_names
    assert "--observed-high-low-order" in option_names
    assert "--known-gap" in option_names
