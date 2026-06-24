from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_collection import register_quote_collection_commands
from support.cli import normalized_stdout


def _recommended_read_order(_data_dir: Path) -> list[str]:
    return ["docs/CURRENT_STATE.md"]


def test_quote_collection_commands_register_standalone() -> None:
    app = typer.Typer()
    register_quote_collection_commands(
        app,
        recommended_read_order_fn=_recommended_read_order,
        trade_xyz_client_factory=lambda: object(),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "collect-trade-xyz-ws" in stdout
    assert "build-trade-xyz-ws-quality" in stdout
    assert "build-trade-xyz-rest-parity" in stdout
    assert "collect-trade-xyz-quotes" in stdout
    assert "collect-trade-xyz-data-cycle" in stdout
    assert "normalize-quotes" in stdout
    assert "normalize-trade-xyz-ws-quotes" in stdout


def test_quote_collection_data_cycle_keeps_safety_options() -> None:
    app = typer.Typer()
    register_quote_collection_commands(
        app,
        recommended_read_order_fn=_recommended_read_order,
        trade_xyz_client_factory=lambda: object(),
    )

    root_command = get_command(app)
    data_cycle_command = root_command.commands["collect-trade-xyz-data-cycle"]
    option_names = {
        option
        for parameter in data_cycle_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--dry-run" in option_names
    assert "--refresh-registry" in option_names
    assert "--use-existing-registry" in option_names
    assert "--allow-known-gaps" in option_names
    assert "--strict" in option_names
