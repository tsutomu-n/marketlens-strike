from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer
from loguru import logger

from sis.models import InstrumentSpec
from sis.settings import get_settings
from sis.storage.normalize import normalize_quotes
from sis.storage.normalize import normalize_trade_xyz_ws_quotes
from sis.venues.trade_xyz.registry import load_trade_xyz_registry


def _csv_items(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def register_quote_normalization_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
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

    @app.command("normalize-trade-xyz-ws-quotes")
    def normalize_trade_xyz_ws_quotes_cmd(
        raw_ws_root: Path | None = typer.Option(
            None,
            "--raw-ws-root",
            help="Trade[XYZ] WS raw root containing partitioned JSONL files.",
        ),
        parquet_path: Path | None = typer.Option(
            None,
            "--parquet-path",
            help="Output parquet path for normalized WS quote rows.",
        ),
        duckdb_path: Path | None = typer.Option(
            None,
            "--duckdb-path",
            help="Output DuckDB path for normalized WS quote rows.",
        ),
        manifest_path: Path | None = typer.Option(
            None,
            "--manifest-path",
            help="Output manifest path for normalized WS quote artifact metadata.",
        ),
        quality_manifest_path: Path | None = typer.Option(
            None,
            "--quality-manifest-path",
            help="Optional source WS quality manifest path to record in the output manifest.",
        ),
        rest_parity_manifest_path: Path | None = typer.Option(
            None,
            "--rest-parity-manifest-path",
            help="Optional source REST parity manifest path to record in the output manifest.",
        ),
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Optional Trade[XYZ] registry JSON for asset_id, real symbol, and fee metadata.",
        ),
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
    ) -> None:
        settings = get_settings()
        effective_raw_ws_root = raw_ws_root or (settings.data_dir / "raw/ws/trade_xyz")
        effective_parquet_path = parquet_path or (
            settings.data_dir / "normalized/trade_xyz_ws_quotes.parquet"
        )
        effective_duckdb_path = duckdb_path or (settings.data_dir / "normalized/sis.duckdb")
        effective_manifest_path = manifest_path or effective_parquet_path.with_suffix(
            ".manifest.json"
        )
        effective_registry_path = registry_path or (
            settings.data_dir / "registry/trade_xyz_instrument_registry.json"
        )
        instruments: list[InstrumentSpec] | None = None
        if effective_registry_path.exists():
            requested_symbols = _csv_items(symbols)
            instruments = load_trade_xyz_registry(effective_registry_path)
            instruments = [
                item
                for item in instruments
                if item.venue.value == "trade_xyz"
                and item.active
                and (
                    requested_symbols is None or item.canonical_symbol.upper() in requested_symbols
                )
            ]
        try:
            count = normalize_trade_xyz_ws_quotes(
                effective_raw_ws_root,
                effective_parquet_path,
                effective_duckdb_path,
                instruments=instruments,
                manifest_path=effective_manifest_path,
                quality_manifest_path=quality_manifest_path,
                rest_parity_manifest_path=rest_parity_manifest_path,
            )
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        logger.info("normalized {} Trade[XYZ] WS quote rows", count)
        typer.echo(f"quote_count={count}")
        typer.echo(f"raw_ws_root={effective_raw_ws_root}")
        typer.echo(f"normalized_ws_quotes_path={effective_parquet_path}")
        typer.echo(f"duckdb_path={effective_duckdb_path}")
        typer.echo(f"manifest_path={effective_manifest_path}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
