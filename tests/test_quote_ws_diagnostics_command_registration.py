from __future__ import annotations

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_ws_diagnostics import register_quote_ws_diagnostic_commands
from support.cli import normalized_stdout


def test_quote_ws_diagnostic_commands_register_standalone() -> None:
    app = typer.Typer()
    register_quote_ws_diagnostic_commands(app, trade_xyz_client_factory=lambda: object())

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "build-trade-xyz-ws-quality" in stdout
    assert "build-trade-xyz-rest-parity" in stdout


def test_trade_xyz_ws_quality_keeps_core_options() -> None:
    app = typer.Typer()
    register_quote_ws_diagnostic_commands(app, trade_xyz_client_factory=lambda: object())

    root_command = get_command(app)
    quality_command = root_command.commands["build-trade-xyz-ws-quality"]
    option_names = {
        option
        for parameter in quality_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--raw-ws-root" in option_names
    assert "--dry-run" in option_names
    assert "--recv-gap-threshold-seconds" in option_names
    assert "--source-gap-threshold-seconds" in option_names


def test_trade_xyz_rest_parity_keeps_core_options() -> None:
    app = typer.Typer()
    register_quote_ws_diagnostic_commands(app, trade_xyz_client_factory=lambda: object())

    root_command = get_command(app)
    parity_command = root_command.commands["build-trade-xyz-rest-parity"]
    option_names = {
        option
        for parameter in parity_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--ws-manifest-path" in option_names
    assert "--symbols" in option_names
    assert "--request-delay-seconds" in option_names
    assert "--include-l2-book" in option_names
    assert "--skip-l2-book" in option_names
    assert "--l2-max-symbols" in option_names
    assert "--dry-run" in option_names


def test_trade_xyz_ws_quality_dry_run_echoes_operator_paths() -> None:
    app = typer.Typer()
    register_quote_ws_diagnostic_commands(app, trade_xyz_client_factory=lambda: object())

    result = CliRunner().invoke(
        app,
        [
            "build-trade-xyz-ws-quality",
            "--dry-run",
            "--raw-ws-root",
            "data/raw/ws/custom",
            "--recv-gap-threshold-seconds",
            "12.5",
            "--source-gap-threshold-seconds",
            "13.5",
        ],
    )

    assert result.exit_code == 0
    assert "dry_run=true" in result.stdout
    assert "raw_ws_root=data/raw/ws/custom" in result.stdout
    assert "recv_gap_threshold_seconds=12.5" in result.stdout
    assert "source_gap_threshold_seconds=13.5" in result.stdout


def test_trade_xyz_rest_parity_dry_run_echoes_operator_inputs() -> None:
    app = typer.Typer()
    register_quote_ws_diagnostic_commands(app, trade_xyz_client_factory=lambda: object())

    result = CliRunner().invoke(
        app,
        [
            "build-trade-xyz-rest-parity",
            "--dry-run",
            "--ws-manifest-path",
            "data/manifests/ws.json",
            "--symbols",
            "SPY,NVDA",
            "--request-delay-seconds",
            "0.4",
            "--include-l2-book",
            "--l2-max-symbols",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "dry_run=true" in result.stdout
    assert "symbols=SPY,NVDA" in result.stdout
    assert "ws_manifest_path=data/manifests/ws.json" in result.stdout
    assert "request_delay_seconds=0.4" in result.stdout
    assert "include_l2_book=True" in result.stdout
    assert "l2_max_symbols=2" in result.stdout
