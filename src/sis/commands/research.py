from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer
from loguru import logger

from sis.reports.cost_matrix import build_cost_matrix_from_quotes, build_cost_matrix_report
from sis.research.event_calendar import build_event_calendar
from sis.research.feature_panel import build_feature_panel
from sis.research.macro_ingest import build_macro_panel
from sis.research.price_ingest import build_market_panel
from sis.research.providers import FredMacroProvider
from sis.research.research_quality import build_research_quality_report
from sis.research.signal_builder import build_signals
from sis.settings import get_settings


def register_research_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("build-cost-matrix")
    def build_cost_matrix() -> None:
        settings = get_settings()
        out = settings.data_dir / "research/venue_cost_matrix.csv"
        build_cost_matrix_from_quotes(
            settings.data_dir / "normalized/quotes.parquet",
            out,
            gtrade_sidecar_root=settings.data_dir / "raw/sidecar/gtrade",
            ostium_registry_path=settings.data_dir / "registry/ostium_instrument_registry.json",
        )
        build_cost_matrix_report(
            cost_matrix_path=out,
            out_path=settings.data_dir / "reports/venue_cost_matrix.md",
            summary_path=settings.data_dir / "ops/venue_cost_matrix_summary.json",
        )
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("ingest-research-data")
    def ingest_research_data() -> None:
        settings = get_settings()
        market_panel = build_market_panel(settings.data_dir)
        macro_panel = build_macro_panel(
            settings.data_dir,
            provider=FredMacroProvider(api_key=settings.fred_api_key),
        )
        logger.info("written: {}", market_panel)
        logger.info("written: {}", macro_panel)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-event-calendar")
    def build_event_calendar_cmd(
        csv_path: Path | None = typer.Option(
            None,
            "--csv-path",
            help="Optional event calendar CSV path. Defaults to data/research/event_calendar.csv.",
        ),
    ) -> None:
        settings = get_settings()
        out = build_event_calendar(settings.data_dir, csv_path=csv_path)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-feature-panel")
    def build_feature_panel_cmd() -> None:
        settings = get_settings()
        out = build_feature_panel(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-signals")
    def build_signals_cmd() -> None:
        settings = get_settings()
        out = build_signals(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("check-research-quality")
    def check_research_quality_cmd() -> None:
        settings = get_settings()
        out = build_research_quality_report(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
