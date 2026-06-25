from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.quotes_window_collection import register_quote_window_collection_commands
from sis.models import InstrumentSpec
from sis.models import Venue
from support.cli import normalized_stdout


def _recommended_read_order(_data_dir: Path) -> list[str]:
    return ["docs/CURRENT_STATE.md"]


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


def test_quote_window_collection_command_registers_standalone() -> None:
    app = typer.Typer()
    register_quote_window_collection_commands(
        app,
        recommended_read_order_fn=_recommended_read_order,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
        trade_xyz_client_factory=lambda: object(),
    )

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--duration-minutes" in stdout
    assert "--interval-seconds" in stdout


def test_quote_window_collection_keeps_core_options() -> None:
    app = typer.Typer()
    register_quote_window_collection_commands(
        app,
        recommended_read_order_fn=_recommended_read_order,
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

    assert "--registry-path" in option_names
    assert "--normalize" in option_names
    assert "--no-normalize" in option_names
    assert "--symbols" in option_names
    assert "--max-symbols" in option_names
    assert "--duration-minutes" in option_names
    assert "--interval-seconds" in option_names
    assert "--replace" in option_names
    assert "--append" in option_names
    assert "--write-summary" in option_names
    assert "--write-report" in option_names
    assert "--output-dir" in option_names
    assert "--dry-run" in option_names


def test_quote_window_collection_dry_run_echoes_operator_inputs() -> None:
    app = typer.Typer()
    register_quote_window_collection_commands(
        app,
        recommended_read_order_fn=_recommended_read_order,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
        trade_xyz_client_factory=lambda: object(),
    )

    result = CliRunner().invoke(
        app,
        [
            "--registry-path",
            "data/registry/custom.json",
            "--symbols",
            "SP500",
            "--duration-minutes",
            "3",
            "--interval-seconds",
            "30",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry_run=true" in result.stdout
    assert "symbol_count=1" in result.stdout
    assert "symbols=SP500" in result.stdout
