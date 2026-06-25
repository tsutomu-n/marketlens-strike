from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_ws_collection import register_quote_ws_collection_commands
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


def test_quote_ws_collection_command_registers_standalone() -> None:
    app = typer.Typer()
    register_quote_ws_collection_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
    )

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "collect-trade-xyz-ws" in stdout


def test_trade_xyz_ws_collection_keeps_core_options() -> None:
    app = typer.Typer()
    register_quote_ws_collection_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
    )

    command = get_command(app)
    option_names = {
        option
        for parameter in command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--collection-config" in option_names
    assert "--registry-path" in option_names
    assert "--symbols" in option_names
    assert "--max-symbols" in option_names
    assert "--subscriptions" in option_names
    assert "--ws-url" in option_names
    assert "--duration-minutes" in option_names
    assert "--heartbeat-seconds" in option_names
    assert "--output-dir" in option_names
    assert "--write-control-messages" in option_names
    assert "--drop-control-messages" in option_names
    assert "--dry-run" in option_names


def test_trade_xyz_ws_collection_dry_run_echoes_operator_inputs() -> None:
    app = typer.Typer()
    register_quote_ws_collection_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
    )

    result = CliRunner().invoke(
        app,
        [
            "--registry-path",
            "data/registry/custom.json",
            "--subscriptions",
            "bbo,allMids",
            "--ws-url",
            "wss://example.test/ws",
            "--duration-minutes",
            "3",
            "--heartbeat-seconds",
            "4",
            "--output-dir",
            "data/raw/ws/custom",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry_run=true" in result.stdout
    assert "registry_path=data/registry/custom.json" in result.stdout
    assert "symbols=SP500" in result.stdout
    assert "subscriptions=bbo,allMids" in result.stdout
    assert "ws_url=wss://example.test/ws" in result.stdout
    assert "heartbeat_seconds=4" in result.stdout
    assert "duration_minutes=3" in result.stdout
    assert "output_dir=data/raw/ws/custom" in result.stdout
