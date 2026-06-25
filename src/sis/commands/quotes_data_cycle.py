from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable
from typing import Protocol

import typer

from sis.models import InstrumentSpec
from sis.settings import get_settings
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import join_csv
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.collector import collect_trade_xyz_quote_window
from sis.venues.trade_xyz.data_bundle import build_trade_xyz_data_collection_bundle
from sis.venues.trade_xyz.registry import build_trade_xyz_registry
from sis.venues.trade_xyz.registry import write_trade_xyz_registry


class ResolveActiveTradeXyzInstrumentsFn(Protocol):
    def __call__(
        self,
        *,
        data_dir: Path,
        registry_path: Path | None,
        symbols: str | None,
        max_symbols: int | None,
    ) -> tuple[Path, list[InstrumentSpec]]: ...


def _refresh_trade_xyz_registry(
    *,
    data_dir: Path,
    seed_path: Path,
    client: TradeXyzClient,
) -> Path:
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    build_result = build_trade_xyz_registry(seed_path, client=client)
    write_trade_xyz_registry(registry_path, build_result)
    return registry_path


def register_quote_data_cycle_commands(
    app: typer.Typer,
    *,
    resolve_active_trade_xyz_instruments_fn: ResolveActiveTradeXyzInstrumentsFn,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
) -> None:
    @app.command("collect-trade-xyz-data-cycle")
    def collect_trade_xyz_data_cycle_cmd(
        collection_config: Path = typer.Option(
            DEFAULT_COLLECTION_CONFIG_PATH,
            "--collection-config",
            help="Non-secret Trade[XYZ] data collection defaults.",
        ),
        seed_path: Path = typer.Option(
            Path("configs/instrument_registry.seed.json"),
            "--seed-path",
            help="Seed file containing venues.trade_xyz rows for optional registry refresh.",
        ),
        refresh_registry: bool = typer.Option(
            True,
            "--refresh-registry/--use-existing-registry",
            help="Refresh the Trade[XYZ] registry from read-only Hyperliquid info endpoints before collecting.",
        ),
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
        duration_minutes: int | None = typer.Option(None, "--duration-minutes"),
        interval_seconds: int | None = typer.Option(None, "--interval-seconds"),
        replace: bool = typer.Option(False, "--replace/--append"),
        write_summary: bool = typer.Option(True, "--write-summary/--no-write-summary"),
        write_report: bool = typer.Option(True, "--write-report/--no-write-report"),
        output_dir: Path | None = typer.Option(None, "--output-dir"),
        min_days: float | None = typer.Option(None, "--min-days"),
        max_gap_minutes: float | None = typer.Option(None, "--max-gap-minutes"),
        max_oracle_lag_minutes: float | None = typer.Option(None, "--max-oracle-lag-minutes"),
        traceable_only: bool = typer.Option(
            True,
            "--traceable-only/--include-untraceable",
            help="Evaluate quote coverage with rows that have raw_payload_ref.",
        ),
        allow_known_gaps: bool = typer.Option(
            False,
            "--allow-known-gaps/--strict",
            help="Allow documented gaps that are out of pure-backtest scope.",
        ),
        collect_real_market_reference_data: bool = typer.Option(
            True,
            "--collect-real-market-reference/--skip-real-market-reference",
            help="Collect read-only real-market reference bars from registry mappings.",
        ),
        collect_signal_candles: bool = typer.Option(
            True,
            "--collect-signal-candles/--skip-signal-candles",
            help="Collect historical candleSnapshot OHLCV for signal inputs, separate from fill snapshots.",
        ),
        signal_candle_intervals: str | None = typer.Option(None, "--signal-candle-intervals"),
        signal_candle_period_days: int | None = typer.Option(None, "--signal-candle-period-days"),
        signal_candle_max_age_hours: float | None = typer.Option(
            None,
            "--signal-candle-max-age-hours",
            help="Reuse existing complete signal candle artifact when it is newer than this.",
        ),
        signal_candle_request_delay_seconds: float | None = typer.Option(
            None,
            "--signal-candle-request-delay-seconds",
            help="Delay between Trade[XYZ] signal candle /info requests.",
        ),
        account_fee_user_address: str | None = typer.Option(
            None,
            "--account-fee-user-address",
            help="Public Hyperliquid user address for optional read-only userFees collection.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
    ) -> None:
        settings = get_settings()
        out_root = output_dir or settings.data_dir
        try:
            config = load_trade_xyz_data_collection_config(collection_config)
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        effective_symbols = symbols or join_csv(config.symbols)
        effective_duration_minutes = duration_minutes or config.duration_minutes
        effective_interval_seconds = interval_seconds or config.interval_seconds
        effective_min_days = min_days if min_days is not None else config.min_days
        effective_max_gap_minutes = (
            max_gap_minutes if max_gap_minutes is not None else config.max_gap_minutes
        )
        effective_max_oracle_lag_minutes = (
            max_oracle_lag_minutes
            if max_oracle_lag_minutes is not None
            else config.max_oracle_lag_minutes
        )
        effective_signal_candle_intervals = signal_candle_intervals or join_csv(
            config.signal_candle_intervals
        )
        effective_signal_candle_period_days = (
            signal_candle_period_days
            if signal_candle_period_days is not None
            else config.signal_candle_period_days
        )
        effective_signal_candle_max_age_hours = (
            signal_candle_max_age_hours
            if signal_candle_max_age_hours is not None
            else config.signal_candle_max_age_hours
        )
        effective_signal_candle_request_delay_seconds = (
            signal_candle_request_delay_seconds
            if signal_candle_request_delay_seconds is not None
            else config.signal_candle_request_delay_seconds
        )
        effective_usable_start_date = (
            date.fromisoformat(config.usable_start_date) if config.usable_start_date else None
        )
        resolved_registry_path = registry_path or (
            settings.data_dir / "registry/trade_xyz_instrument_registry.json"
        )
        if refresh_registry and registry_path is not None:
            typer.echo("--refresh-registry cannot be used with --registry-path")
            raise typer.Exit(code=2)
        if refresh_registry and not seed_path.exists():
            typer.echo(f"trade_xyz seed file not found: {seed_path}")
            raise typer.Exit(code=2)

        if refresh_registry and dry_run:
            resolved_registry_path = (
                settings.data_dir / "registry/trade_xyz_instrument_registry.json"
            )
        if refresh_registry and not dry_run:
            with trade_xyz_client_factory() as client:
                resolved_registry_path = _refresh_trade_xyz_registry(
                    data_dir=settings.data_dir,
                    seed_path=seed_path,
                    client=client,
                )

        try:
            resolved_registry_path, active_trade_xyz = resolve_active_trade_xyz_instruments_fn(
                data_dir=settings.data_dir,
                registry_path=resolved_registry_path,
                symbols=effective_symbols,
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

        if effective_duration_minutes <= 0 or effective_interval_seconds <= 0:
            typer.echo("duration-minutes and interval-seconds must be > 0")
            raise typer.Exit(code=2)
        if effective_duration_minutes * 60 < effective_interval_seconds:
            typer.echo("duration-minutes * 60 must be >= interval-seconds")
            raise typer.Exit(code=2)

        requested_symbols = [item.canonical_symbol.upper() for item in active_trade_xyz]
        if dry_run:
            typer.echo("dry_run=true")
            typer.echo(f"symbol_count={len(active_trade_xyz)}")
            typer.echo(f"symbols={','.join(requested_symbols)}")
            typer.echo(f"registry_refresh={'enabled' if refresh_registry else 'disabled'}")
            if refresh_registry:
                typer.echo(f"registry_seed_path={seed_path}")
                typer.echo(f"registry_path={resolved_registry_path}")
            typer.echo(
                "collect_command="
                "uv run sis collect-trade-xyz-quotes "
                f"--duration-minutes {effective_duration_minutes} "
                f"--interval-seconds {effective_interval_seconds} "
                "--write-summary --write-report "
                f"--symbols {','.join(requested_symbols)}"
            )
            typer.echo(
                "follow_up_command=uv run sis build-trade-xyz-data-bundle --auto-funding-window"
            )
            typer.echo(
                "signal_candles="
                f"{'enabled' if collect_signal_candles else 'disabled'} "
                f"intervals={effective_signal_candle_intervals} "
                f"period_days={effective_signal_candle_period_days} "
                f"request_delay_seconds={effective_signal_candle_request_delay_seconds}"
            )
            if account_fee_user_address:
                typer.echo("account_fee_collection=enabled")
            return

        with trade_xyz_client_factory() as client:
            summary = collect_trade_xyz_quote_window(
                data_dir=settings.data_dir,
                instruments=active_trade_xyz,
                duration_minutes=effective_duration_minutes,
                interval_seconds=effective_interval_seconds,
                normalize=normalize,
                replace=replace,
                write_summary=write_summary,
                write_report=write_report,
                output_dir=output_dir,
                client=client,
            )
            bundle = build_trade_xyz_data_collection_bundle(
                data_dir=out_root,
                registry_path=resolved_registry_path,
                raw_quotes_root=out_root / "raw/quotes",
                symbols=requested_symbols,
                min_days=effective_min_days,
                max_gap_minutes=effective_max_gap_minutes,
                traceable_only=traceable_only,
                max_oracle_lag_minutes=effective_max_oracle_lag_minutes,
                auto_funding_window=True,
                funding_client=client,
                account_fee_user_address=account_fee_user_address,
                account_fee_client=client,
                collect_signal_candles=collect_signal_candles,
                signal_candle_intervals=[
                    item.strip()
                    for item in effective_signal_candle_intervals.split(",")
                    if item.strip()
                ],
                signal_candle_period_days=effective_signal_candle_period_days,
                signal_candle_max_age_hours=effective_signal_candle_max_age_hours,
                signal_candle_request_delay_seconds=effective_signal_candle_request_delay_seconds,
                signal_candle_client=client,
                collect_real_market_reference_data=collect_real_market_reference_data,
                usable_start_date=effective_usable_start_date,
                allow_known_gaps=allow_known_gaps,
            )

        typer.echo(f"quote_count={summary['row_count']}")
        typer.echo(f"raw_quotes_path={summary['raw_quotes_path']}")
        if normalize:
            typer.echo(f"normalized_quotes_path={summary['normalized_quotes_path']}")
            typer.echo(f"duckdb_path={summary['duckdb_path']}")
        if write_summary:
            typer.echo(f"summary_path={out_root / 'ops/trade_xyz_quote_collection_summary.json'}")
        if write_report:
            typer.echo(f"report_path={summary.get('report_path')}")
        typer.echo(
            "bundle_manifest_path="
            f"{out_root / 'manifests/trade_xyz_data_collection_bundle_manifest.json'}"
        )
        typer.echo(f"readiness_decision={bundle['readiness_decision']}")
        typer.echo(f"backtest_data_ready={bundle['backtest_data_ready']}")
        typer.echo(f"failed_step_count={bundle['failed_step_count']}")
