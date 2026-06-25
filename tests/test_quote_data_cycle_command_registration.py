from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_data_cycle import register_quote_data_cycle_commands
from sis.models import InstrumentSpec
from sis.models import Venue
from support.cli import normalized_stdout


def _resolve_active_trade_xyz_instruments(
    *,
    data_dir: Path,
    registry_path: Path | None,
    symbols: str | None,
    max_symbols: int | None,
) -> tuple[Path, list[InstrumentSpec]]:
    _ = data_dir, symbols, max_symbols
    return (
        registry_path or Path("data/registry/trade_xyz_instrument_registry.json"),
        [
            InstrumentSpec(
                venue=Venue.TRADE_XYZ,
                canonical_symbol="SP500",
                venue_symbol="SP500",
                asset_class="index",
                dex="xyz",
                coin="xyz:SP500",
                asset_id=130001,
                real_market_symbol="SPY",
                active=True,
            )
        ],
    )


def test_quote_data_cycle_command_registers_standalone() -> None:
    app = typer.Typer()
    register_quote_data_cycle_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
        trade_xyz_client_factory=lambda: object(),
    )

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--collection-config" in stdout
    assert "--refresh-registry" in stdout


def test_quote_data_cycle_keeps_safety_options() -> None:
    app = typer.Typer()
    register_quote_data_cycle_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
        trade_xyz_client_factory=lambda: object(),
    )

    command = get_command(app)
    option_names = {
        option
        for parameter in command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--dry-run" in option_names
    assert "--refresh-registry" in option_names
    assert "--use-existing-registry" in option_names
    assert "--allow-known-gaps" in option_names
    assert "--strict" in option_names
    assert "--collect-signal-candles" in option_names
    assert "--skip-signal-candles" in option_names
    assert "--account-fee-user-address" in option_names


def test_quote_data_cycle_dry_run_echoes_operator_inputs() -> None:
    app = typer.Typer()
    register_quote_data_cycle_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
        trade_xyz_client_factory=lambda: object(),
    )

    result = CliRunner().invoke(
        app,
        [
            "--collection-config",
            "configs/trade_xyz_data_collection.yaml",
            "--use-existing-registry",
            "--registry-path",
            "data/registry/custom.json",
            "--symbols",
            "SP500",
            "--duration-minutes",
            "5",
            "--interval-seconds",
            "60",
            "--signal-candle-request-delay-seconds",
            "0",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry_run=true" in result.stdout
    assert "symbol_count=1" in result.stdout
    assert "symbols=SP500" in result.stdout
    assert "registry_refresh=disabled" in result.stdout
    assert "collect_command=uv run sis collect-trade-xyz-quotes" in result.stdout
    assert "--duration-minutes 5" in result.stdout
    assert "--interval-seconds 60" in result.stdout
    assert "request_delay_seconds=0.0" in result.stdout
