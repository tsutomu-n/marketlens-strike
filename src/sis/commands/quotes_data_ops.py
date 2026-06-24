from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer

from sis.settings import get_settings
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.funding_history import (
    build_trade_xyz_backtest_funding_events_from_history,
    collect_trade_xyz_funding_history,
)
from sis.venues.trade_xyz.readiness import build_trade_xyz_data_readiness_manifest
from sis.venues.trade_xyz.session_state import build_trade_xyz_session_state_observations


def _csv_items(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def register_quote_data_ops_commands(
    app: typer.Typer,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
) -> None:
    @app.command("build-trade-xyz-session-state")
    def build_trade_xyz_session_state_cmd(
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        raw_quotes_root: Path | None = typer.Option(
            None,
            "--raw-quotes-root",
            help="Raw quotes root containing trade_xyz/*.jsonl.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            manifest = build_trade_xyz_session_state_observations(
                data_dir=settings.data_dir,
                registry_path=registry_path,
                raw_quotes_root=raw_quotes_root,
            )
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(f"manifest_path={settings.data_dir / 'manifests/session_state_manifest.json'}")
        typer.echo(f"artifact_path={manifest['artifact_path']}")
        typer.echo(f"row_count={manifest['row_count']}")
        typer.echo(f"session_type_counts={manifest['session_type_counts']}")

    @app.command("collect-trade-xyz-funding-history")
    def collect_trade_xyz_funding_history_cmd(
        start_time_ms: int = typer.Option(..., "--start-time-ms"),
        end_time_ms: int | None = typer.Option(None, "--end-time-ms"),
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
    ) -> None:
        settings = get_settings()
        requested_symbols = _csv_items(symbols)
        try:
            with trade_xyz_client_factory() as client:
                manifest = collect_trade_xyz_funding_history(
                    data_dir=settings.data_dir,
                    registry_path=registry_path,
                    symbols=requested_symbols,
                    start_time_ms=start_time_ms,
                    end_time_ms=end_time_ms,
                    client=client,
                )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(f"manifest_path={settings.data_dir / 'manifests/funding_history_manifest.json'}")
        typer.echo(f"artifact_path={manifest['artifact_path']}")
        typer.echo(f"row_count={manifest['row_count']}")
        typer.echo(
            f"usable_as_backtest_funding_event={manifest['usable_as_backtest_funding_event']}"
        )

    @app.command("build-trade-xyz-funding-events-from-history")
    def build_trade_xyz_funding_events_from_history_cmd(
        funding_history_path: Path | None = typer.Option(
            None,
            "--funding-history-path",
            help="Parquet written by collect-trade-xyz-funding-history.",
        ),
        raw_quotes_root: Path | None = typer.Option(
            None,
            "--raw-quotes-root",
            help="Raw quotes root containing trade_xyz/*.jsonl.",
        ),
        max_oracle_lag_minutes: float = typer.Option(90.0, "--max-oracle-lag-minutes"),
    ) -> None:
        settings = get_settings()
        try:
            manifest = build_trade_xyz_backtest_funding_events_from_history(
                data_dir=settings.data_dir,
                funding_history_path=funding_history_path,
                raw_quotes_root=raw_quotes_root,
                max_oracle_lag_minutes=max_oracle_lag_minutes,
            )
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            f"manifest_path={settings.data_dir / 'manifests/funding_history_join_manifest.json'}"
        )
        typer.echo(f"artifact_path={manifest['artifact_path']}")
        typer.echo(f"row_count={manifest['row_count']}")
        typer.echo(f"history_row_count={manifest['history_row_count']}")
        typer.echo(
            f"usable_as_backtest_funding_event={manifest['usable_as_backtest_funding_event']}"
        )

    @app.command("build-trade-xyz-data-readiness")
    def build_trade_xyz_data_readiness_cmd(
        allow_known_gaps: bool = typer.Option(
            False,
            "--allow-known-gaps/--strict",
            help="Allow documented gaps that are out of pure-backtest scope.",
        ),
    ) -> None:
        settings = get_settings()
        manifest = build_trade_xyz_data_readiness_manifest(
            data_dir=settings.data_dir,
            allow_known_gaps=allow_known_gaps,
        )
        typer.echo(
            f"manifest_path={settings.data_dir / 'manifests/trade_xyz_data_readiness_manifest.json'}"
        )
        typer.echo(f"decision={manifest['decision']}")
        typer.echo(f"backtest_data_ready={manifest['backtest_data_ready']}")
        typer.echo(f"fail_count={manifest['fail_count']}")
        typer.echo(f"known_gap_count={manifest['known_gap_count']}")
