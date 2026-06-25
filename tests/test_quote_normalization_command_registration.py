from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_normalization import register_quote_normalization_commands
from support.cli import normalized_stdout


def _recommended_read_order(_data_dir: Path) -> list[str]:
    return ["docs/CURRENT_STATE.md"]


def test_quote_normalization_commands_register_standalone() -> None:
    app = typer.Typer()
    register_quote_normalization_commands(app, recommended_read_order_fn=_recommended_read_order)

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "normalize-quotes" in stdout
    assert "normalize-trade-xyz-ws-quotes" in stdout


def test_trade_xyz_ws_normalization_keeps_core_options() -> None:
    app = typer.Typer()
    register_quote_normalization_commands(app, recommended_read_order_fn=_recommended_read_order)

    root_command = get_command(app)
    ws_command = root_command.commands["normalize-trade-xyz-ws-quotes"]
    option_names = {
        option
        for parameter in ws_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--raw-ws-root" in option_names
    assert "--parquet-path" in option_names
    assert "--duckdb-path" in option_names
    assert "--manifest-path" in option_names
    assert "--quality-manifest-path" in option_names
    assert "--rest-parity-manifest-path" in option_names
    assert "--registry-path" in option_names
    assert "--symbols" in option_names
