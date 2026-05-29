from __future__ import annotations

from datetime import datetime, timezone
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
from sis.real_market.alpaca_smoke import run_alpaca_live_smoke
from sis.settings import get_settings


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


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
        macro_provider = (
            FredMacroProvider(api_key=settings.fred_api_key) if settings.fred_api_key else None
        )
        macro_panel = build_macro_panel(settings.data_dir, provider=macro_provider)
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

    @app.command("alpaca-smoke")
    def alpaca_smoke_cmd(
        symbol: str = typer.Option("NVDA", "--symbol", help="Alpaca stock symbol."),
        timeframe: str = typer.Option("15m", "--timeframe", help="Alpaca bars timeframe."),
        start: str | None = typer.Option(
            None,
            "--start",
            help="Optional ISO start time for historical connectivity smoke.",
        ),
        end: str | None = typer.Option(
            None,
            "--end",
            help="Optional ISO end time for historical connectivity smoke.",
        ),
        limit: int = typer.Option(1, "--limit", min=1, help="Number of bars to request."),
        feed: str = typer.Option("iex", "--feed", help="Alpaca data feed."),
        timeout: float = typer.Option(10.0, "--timeout", min=0.1, help="Request timeout seconds."),
        raw_payload_path: Path | None = typer.Option(
            None,
            "--raw-payload-path",
            help="Optional raw payload output path. Defaults under data/raw/real_market/alpaca.",
        ),
    ) -> None:
        settings = get_settings()
        summary = run_alpaca_live_smoke(
            data_dir=settings.data_dir,
            symbol=symbol,
            timeframe=timeframe,
            start=_parse_optional_datetime(start),
            end=_parse_optional_datetime(end),
            limit=limit,
            feed=feed,
            timeout=timeout,
            raw_payload_path=raw_payload_path,
        )
        typer.echo(f"status={summary['status']}")
        typer.echo(f"provider_connectivity_status={summary['provider_connectivity_status']}")
        typer.echo(f"data_availability_status={summary['data_availability_status']}")
        typer.echo(f"symbol={summary['symbol']}")
        typer.echo(f"timeframe={summary['timeframe']}")
        typer.echo(f"effective_timeframe={summary['effective_timeframe']}")
        typer.echo(f"feed={summary['feed']}")
        typer.echo(f"requested_window={summary['requested_window']}")
        typer.echo(f"request_endpoint={summary['request_endpoint']}")
        typer.echo(f"start={summary['start']}")
        typer.echo(f"end={summary['end']}")
        typer.echo(f"bar_count={summary['bar_count']}")
        typer.echo(f"latest_bar_ts={summary.get('latest_bar_ts')}")
        typer.echo(f"market_session={summary.get('market_session')}")
        typer.echo(f"source_confidence={summary['source_confidence']}")
        typer.echo(f"source_confidence_reason={summary.get('source_confidence_reason')}")
        live_suitability_reasons = summary.get("live_suitability_reasons")
        formatted_reasons = (
            ",".join(str(reason) for reason in live_suitability_reasons)
            if isinstance(live_suitability_reasons, list)
            else ""
        )
        typer.echo(f"live_suitability_reasons={formatted_reasons}")
        typer.echo(f"summary_path={summary['summary_path']}")
        typer.echo(f"report_path={summary['report_path']}")
        typer.echo(f"raw_payload_path={summary['raw_payload_path']}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
        if summary.get("status") != "pass":
            typer.echo(f"error_class={summary.get('error_class')}")
            typer.echo(f"error_message={summary.get('error_message')}")
            raise typer.Exit(2)
