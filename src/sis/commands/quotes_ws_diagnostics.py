from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer

from sis.settings import get_settings
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.rest_parity import build_trade_xyz_rest_parity_manifest
from sis.venues.trade_xyz.ws_quality import build_trade_xyz_ws_quality_manifest


def register_quote_ws_diagnostic_commands(
    app: typer.Typer,
    *,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
) -> None:
    @app.command("build-trade-xyz-ws-quality")
    def build_trade_xyz_ws_quality_cmd(
        raw_ws_root: Path | None = typer.Option(
            None,
            "--raw-ws-root",
            help="WS raw root under data/raw/ws/trade_xyz.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        recv_gap_threshold_seconds: float = typer.Option(
            60.0,
            "--recv-gap-threshold-seconds",
            min=0.0,
            help="Warn only when recv_ts gaps exceed this threshold.",
        ),
        source_gap_threshold_seconds: float = typer.Option(
            60.0,
            "--source-gap-threshold-seconds",
            min=0.0,
            help="Warn only when source_ts gaps exceed this threshold.",
        ),
    ) -> None:
        settings = get_settings()
        path = raw_ws_root or (settings.data_dir / "raw/ws/trade_xyz")
        if dry_run:
            typer.echo("dry_run=true")
            typer.echo(f"raw_ws_root={path}")
            typer.echo(
                f"manifest_path={settings.data_dir / 'manifests/trade_xyz_ws_quality_manifest.json'}"
            )
            typer.echo(f"recv_gap_threshold_seconds={recv_gap_threshold_seconds}")
            typer.echo(f"source_gap_threshold_seconds={source_gap_threshold_seconds}")
            return
        manifest = build_trade_xyz_ws_quality_manifest(
            data_dir=settings.data_dir,
            raw_ws_root=path,
            recv_gap_threshold_seconds=recv_gap_threshold_seconds,
            source_gap_threshold_seconds=source_gap_threshold_seconds,
        )
        typer.echo(
            f"manifest_path={settings.data_dir / 'manifests/trade_xyz_ws_quality_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"row_count={manifest['row_count']}")

    @app.command("build-trade-xyz-rest-parity")
    def build_trade_xyz_rest_parity_cmd(
        ws_manifest_path: Path | None = typer.Option(
            None,
            "--ws-manifest-path",
            help="WS capture manifest path.",
        ),
        symbols: str | None = typer.Option(None, "--symbols"),
        request_delay_seconds: float = typer.Option(0.2, "--request-delay-seconds"),
        include_l2_book: bool = typer.Option(False, "--include-l2-book/--skip-l2-book"),
        l2_max_symbols: int = typer.Option(3, "--l2-max-symbols"),
        dry_run: bool = typer.Option(False, "--dry-run"),
    ) -> None:
        settings = get_settings()
        config = load_trade_xyz_data_collection_config(DEFAULT_COLLECTION_CONFIG_PATH)
        effective_ws_manifest_path = ws_manifest_path or (
            settings.data_dir / "manifests/trade_xyz_ws_capture_manifest.json"
        )
        requested_symbols = (
            [item.strip().upper() for item in symbols.split(",") if item.strip()]
            if symbols
            else list(config.symbols)
        )
        if dry_run:
            typer.echo("dry_run=true")
            typer.echo(f"symbols={','.join(requested_symbols)}")
            typer.echo(f"ws_manifest_path={effective_ws_manifest_path}")
            typer.echo(f"request_delay_seconds={request_delay_seconds}")
            typer.echo(f"include_l2_book={include_l2_book}")
            typer.echo(f"l2_max_symbols={l2_max_symbols}")
            return
        with trade_xyz_client_factory() as client:
            manifest = build_trade_xyz_rest_parity_manifest(
                data_dir=settings.data_dir,
                ws_manifest_path=effective_ws_manifest_path,
                symbols=requested_symbols,
                client=client,
                request_delay_seconds=request_delay_seconds,
                include_l2_book=include_l2_book,
                l2_max_symbols=l2_max_symbols,
            )
        typer.echo(
            f"manifest_path={settings.data_dir / 'manifests/trade_xyz_rest_parity_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"request_error_count={manifest['request_error_count']}")
        typer.echo(f"missing_rest_symbols={','.join(manifest['missing_rest_symbols'])}")
