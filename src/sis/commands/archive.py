from __future__ import annotations

from datetime import datetime, timezone

import typer

from sis.settings import get_settings
from sis.venues.archive.ostium.constraints import (
    DEFAULT_BUILDER_PRICES_ENDPOINT,
    DEFAULT_LATEST_PRICE_ENDPOINT,
    DEFAULT_LATEST_PRICES_ENDPOINT,
    DEFAULT_TRADING_HOURS_ENDPOINT,
    write_ostium_constraint_artifact,
)


def register_archive_commands(app: typer.Typer) -> None:
    @app.command("ostium-constraint-artifact")
    def ostium_constraint_artifact(
        run_id: str = typer.Option(
            datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            "--run-id",
            help="Run id used in Ostium constraint artifact filenames.",
        ),
        assets: list[str] = typer.Option(
            ["SPX", "NDX", "XAU"],
            "--asset",
            help="Ostium asset symbol to collect. Repeat for multiple assets.",
        ),
        latest_prices_endpoint: str = typer.Option(
            DEFAULT_LATEST_PRICES_ENDPOINT,
            "--latest-prices-endpoint",
        ),
        latest_price_endpoint: str = typer.Option(
            DEFAULT_LATEST_PRICE_ENDPOINT,
            "--latest-price-endpoint",
        ),
        trading_hours_endpoint: str = typer.Option(
            DEFAULT_TRADING_HOURS_ENDPOINT,
            "--trading-hours-endpoint",
        ),
        builder_prices_endpoint: str = typer.Option(
            DEFAULT_BUILDER_PRICES_ENDPOINT,
            "--builder-prices-endpoint",
        ),
    ) -> None:
        settings = get_settings()
        result = write_ostium_constraint_artifact(
            data_dir=settings.data_dir,
            run_id=run_id,
            assets=tuple(assets),
            latest_prices_endpoint=latest_prices_endpoint,
            latest_price_endpoint=latest_price_endpoint,
            trading_hours_endpoint=trading_hours_endpoint,
            builder_prices_endpoint=builder_prices_endpoint,
        )
        typer.echo(f"constraint_status={result['constraint_status']}")
        typer.echo(f"artifact_path={result['artifact_path']}")
        typer.echo(f"summary_path={result['summary_path']}")
