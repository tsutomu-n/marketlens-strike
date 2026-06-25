from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer

from sis.commands.quotes_data_cycle import register_quote_data_cycle_commands
from sis.commands.quotes_normalization import register_quote_normalization_commands
from sis.commands.quotes_window_collection import register_quote_window_collection_commands
from sis.commands.quotes_ws_collection import register_quote_ws_collection_commands
from sis.commands.quotes_ws_diagnostics import register_quote_ws_diagnostic_commands
from sis.models import InstrumentSpec
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.registry import load_trade_xyz_registry


def _resolve_active_trade_xyz_instruments(
    *,
    data_dir: Path,
    registry_path: Path | None,
    symbols: str | None,
    max_symbols: int | None,
) -> tuple[Path, list[InstrumentSpec]]:
    resolved_registry_path = registry_path or (
        data_dir / "registry/trade_xyz_instrument_registry.json"
    )
    instruments = load_trade_xyz_registry(resolved_registry_path)
    active_trade_xyz = [
        instrument
        for instrument in instruments
        if instrument.venue.value == "trade_xyz" and instrument.active
    ]
    if symbols:
        requested = [item.strip().upper() for item in symbols.split(",") if item.strip()]
        available = {item.canonical_symbol.upper(): item for item in active_trade_xyz}
        missing = [item for item in requested if item not in available]
        if missing:
            raise ValueError(f"symbols not found in trade_xyz registry: {','.join(missing)}")
        active_trade_xyz = [available[item] for item in requested]
    if max_symbols is not None:
        active_trade_xyz = active_trade_xyz[:max_symbols]
    if not active_trade_xyz:
        raise ValueError("no active trade_xyz instruments found in registry")
    return resolved_registry_path, active_trade_xyz


def register_quote_collection_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
    *,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
) -> None:
    register_quote_normalization_commands(app, recommended_read_order_fn)
    register_quote_ws_collection_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
    )
    register_quote_ws_diagnostic_commands(
        app,
        trade_xyz_client_factory=trade_xyz_client_factory,
    )
    register_quote_window_collection_commands(
        app,
        recommended_read_order_fn,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
        trade_xyz_client_factory=trade_xyz_client_factory,
    )
    register_quote_data_cycle_commands(
        app,
        resolve_active_trade_xyz_instruments_fn=_resolve_active_trade_xyz_instruments,
        trade_xyz_client_factory=trade_xyz_client_factory,
    )
