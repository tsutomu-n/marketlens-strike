from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer

from sis.commands.quotes_collection import register_quote_collection_commands
from sis.commands.quotes_collection_status import register_quote_collection_status_commands
from sis.commands.quotes_data_bundle import register_quote_data_bundle_commands
from sis.commands.quotes_data_ops import register_quote_data_ops_commands
from sis.commands.quotes_historical_archive import register_quote_historical_archive_commands
from sis.commands.quotes_reference import register_quote_reference_commands
from sis.venues.trade_xyz.client import TradeXyzClient


def register_quote_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    register_quote_collection_commands(
        app,
        recommended_read_order_fn,
        trade_xyz_client_factory=lambda: TradeXyzClient(),
    )
    register_quote_reference_commands(app, trade_xyz_client_factory=lambda: TradeXyzClient())
    register_quote_historical_archive_commands(app)
    register_quote_data_ops_commands(app, trade_xyz_client_factory=lambda: TradeXyzClient())
    register_quote_data_bundle_commands(app, trade_xyz_client_factory=lambda: TradeXyzClient())
    register_quote_collection_status_commands(app)
