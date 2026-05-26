from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import typer
from loguru import logger

from sis.settings import get_settings
from sis.storage.normalize import normalize_quotes
from sis.venues.archive.gtrade.quotes import (
    convert_sidecar_to_quote_logs,
    latest_pricing_file,
    latest_sidecar_file,
)


def register_quote_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("log-quotes")
    def log_quotes(
        venue: str = typer.Option(..., "--venue"),
        replace: bool = typer.Option(
            False,
            "--replace",
            help="Replace the generated daily quote JSONL before replaying the sidecar.",
        ),
    ) -> None:
        settings = get_settings()
        normalized_venue = venue.strip().lower()
        if normalized_venue != "gtrade":
            typer.echo("Only gtrade sidecar ingestion is available in the initial scaffold.")
            raise typer.Exit(code=2)

        try:
            sidecar = latest_sidecar_file(settings.data_dir / "raw/sidecar/gtrade")
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        day = datetime.now(timezone.utc).date().isoformat()
        out = settings.data_dir / f"raw/quotes/gtrade/{day}.jsonl"
        if replace and out.exists():
            out.unlink()
        pricing = None
        pricing_root = settings.data_dir / "raw/sidecar/gtrade-pricing"
        if pricing_root.exists():
            try:
                pricing = latest_pricing_file(pricing_root)
            except FileNotFoundError:
                pricing = None
        count = convert_sidecar_to_quote_logs(sidecar, out, pricing_path=pricing)
        logger.info("written {} quote rows: {}", count, out)
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
