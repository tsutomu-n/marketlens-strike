from __future__ import annotations

from pathlib import Path
from typing import Callable
from typing import Protocol

import typer
from loguru import logger

from sis.models import InstrumentSpec
from sis.settings import get_settings
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.collector import collect_trade_xyz_quote_window


class ResolveActiveTradeXyzInstrumentsFn(Protocol):
    def __call__(
        self,
        *,
        data_dir: Path,
        registry_path: Path | None,
        symbols: str | None,
        max_symbols: int | None,
    ) -> tuple[Path, list[InstrumentSpec]]: ...


def register_quote_window_collection_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
    *,
    resolve_active_trade_xyz_instruments_fn: ResolveActiveTradeXyzInstrumentsFn,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
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
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        max_symbols: int | None = typer.Option(None, "--max-symbols"),
        duration_minutes: int = typer.Option(1, "--duration-minutes"),
        interval_seconds: int = typer.Option(60, "--interval-seconds"),
        replace: bool = typer.Option(False, "--replace/--append"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        write_summary: bool = typer.Option(False, "--write-summary/--no-write-summary"),
        write_report: bool = typer.Option(False, "--write-report/--no-write-report"),
        output_dir: Path | None = typer.Option(None, "--output-dir"),
    ) -> None:
        settings = get_settings()
        try:
            _resolved_registry_path, active_trade_xyz = resolve_active_trade_xyz_instruments_fn(
                data_dir=settings.data_dir,
                registry_path=registry_path,
                symbols=symbols,
                max_symbols=max_symbols,
            )
        except FileNotFoundError:
            resolved_registry_path = registry_path or (
                settings.data_dir / "registry/trade_xyz_instrument_registry.json"
            )
            typer.echo(
                f"trade_xyz registry not found: {resolved_registry_path}. "
                "Run `uv run sis probe trade-xyz` first or pass --registry-path."
            )
            raise typer.Exit(code=2)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc

        if duration_minutes <= 0 or interval_seconds <= 0:
            typer.echo("duration-minutes and interval-seconds must be > 0")
            raise typer.Exit(code=2)
        if duration_minutes * 60 < interval_seconds:
            typer.echo("duration-minutes * 60 must be >= interval-seconds")
            raise typer.Exit(code=2)

        if dry_run:
            typer.echo("dry_run=true")
            typer.echo(f"symbol_count={len(active_trade_xyz)}")
            typer.echo(f"symbols={','.join(item.canonical_symbol for item in active_trade_xyz)}")
            return

        with trade_xyz_client_factory() as client:
            summary = collect_trade_xyz_quote_window(
                data_dir=settings.data_dir,
                instruments=active_trade_xyz,
                duration_minutes=duration_minutes,
                interval_seconds=interval_seconds,
                normalize=normalize,
                replace=replace,
                write_summary=write_summary,
                write_report=write_report,
                output_dir=output_dir,
                client=client,
            )
        logger.info("written {} trade_xyz quote rows", summary["row_count"])
        typer.echo(f"quote_count={summary['row_count']}")
        typer.echo(f"raw_quotes_path={summary['raw_quotes_path']}")
        if normalize:
            typer.echo(f"normalized_quotes_path={summary['normalized_quotes_path']}")
            typer.echo(f"duckdb_path={summary['duckdb_path']}")
        if write_summary:
            typer.echo(
                f"summary_path={(output_dir or settings.data_dir) / 'ops/trade_xyz_quote_collection_summary.json'}"
            )
        if write_report:
            typer.echo(f"report_path={summary.get('report_path')}")

        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
