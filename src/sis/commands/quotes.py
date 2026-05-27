from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import typer
from loguru import logger

from sis.settings import get_settings
from sis.storage.normalize import normalize_quotes
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.collector import collect_trade_xyz_quotes
from sis.venues.trade_xyz.registry import load_trade_xyz_registry


def register_quote_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("collect-trade-xyz-quotes")
    def collect_trade_xyz_quotes_cmd(
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        normalize: bool = typer.Option(
            True,
            "--normalize/--no-normalize",
            help="Normalize raw quote JSONL into parquet and DuckDB after collection.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_registry_path = registry_path or (
            settings.data_dir / "registry/trade_xyz_instrument_registry.json"
        )
        try:
            instruments = load_trade_xyz_registry(resolved_registry_path)
        except FileNotFoundError:
            typer.echo(
                f"trade_xyz registry not found: {resolved_registry_path}. "
                "Run `uv run sis probe trade-xyz` first or pass --registry-path."
            )
            raise typer.Exit(code=2)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc

        active_trade_xyz = [
            instrument
            for instrument in instruments
            if instrument.venue.value == "trade_xyz" and instrument.active
        ]
        if not active_trade_xyz:
            typer.echo("no active trade_xyz instruments found in registry")
            raise typer.Exit(code=2)

        day = datetime.now(timezone.utc).date().isoformat()
        raw_quotes_path = settings.data_dir / f"raw/quotes/trade_xyz/{day}.jsonl"
        normalized_quotes_path = settings.data_dir / "normalized/quotes.parquet"
        duckdb_path = settings.data_dir / "normalized/sis.duckdb"

        with TradeXyzClient() as client:
            quote_count = collect_trade_xyz_quotes(
                instruments=active_trade_xyz,
                out_path=raw_quotes_path,
                client=client,
            )

        logger.info("written {} trade_xyz quote rows: {}", quote_count, raw_quotes_path)
        typer.echo(f"quote_count={quote_count}")
        typer.echo(f"raw_quotes_path={raw_quotes_path}")

        if normalize:
            normalized_count = normalize_quotes(
                settings.data_dir / "raw/quotes",
                normalized_quotes_path,
                duckdb_path,
            )
            logger.info("normalized {} quote rows", normalized_count)
            typer.echo(f"normalized_quotes_path={normalized_quotes_path}")
            typer.echo(f"duckdb_path={duckdb_path}")

        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("normalize-quotes")
    def normalize_quotes_cmd() -> None:
        settings = get_settings()
        try:
            count = normalize_quotes(
                settings.data_dir / "raw/quotes",
                settings.data_dir / "normalized/quotes.parquet",
                settings.data_dir / "normalized/sis.duckdb",
            )
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        logger.info("normalized {} quote rows", count)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
