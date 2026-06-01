from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import shlex
from typing import Callable

import typer
from loguru import logger

from sis.models import InstrumentSpec
from sis.settings import get_settings
from sis.storage.normalize import normalize_quotes
from sis.venues.trade_xyz.account_fee import collect_trade_xyz_account_fee_snapshot
from sis.venues.trade_xyz.candles import collect_trade_xyz_signal_candles
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import join_csv
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.collection_status import build_trade_xyz_collection_status
from sis.venues.trade_xyz.collector import collect_trade_xyz_quote_window
from sis.venues.trade_xyz.coverage import build_trade_xyz_quote_coverage_manifest
from sis.venues.trade_xyz.data_bundle import build_trade_xyz_data_collection_bundle
from sis.venues.trade_xyz.funding_history import (
    build_trade_xyz_backtest_funding_events_from_history,
    collect_trade_xyz_funding_history,
)
from sis.venues.trade_xyz.historical_archive import (
    HistoricalL2ArchiveRequest,
    build_hyperliquid_historical_archive_bulk_plan,
    collect_hyperliquid_historical_asset_ctxs_archive,
    collect_hyperliquid_historical_l2_archive,
    check_hyperliquid_historical_archive_preflight,
    execute_hyperliquid_historical_archive_bulk_plan,
    normalize_historical_archive_bulk_to_trade_xyz_quotes,
    normalize_historical_archive_to_trade_xyz_quotes,
)
from sis.venues.trade_xyz.reference_data import build_trade_xyz_reference_datasets
from sis.venues.trade_xyz.real_market_reference import (
    collect_trade_xyz_real_market_reference,
)
from sis.venues.trade_xyz.readiness import build_trade_xyz_data_readiness_manifest
from sis.venues.trade_xyz.registry import build_trade_xyz_registry
from sis.venues.trade_xyz.registry import load_trade_xyz_registry
from sis.venues.trade_xyz.registry import write_trade_xyz_registry
from sis.venues.trade_xyz.session_state import build_trade_xyz_session_state_observations


def _resolve_active_trade_xyz_instruments(
    *,
    data_dir: Path,
    registry_path: Path | None,
    symbols: str | None,
    max_symbols: int | None,
) -> tuple[Path, list[InstrumentSpec]]:
    resolved_registry_path = registry_path or (
        data_dir / "registry/trade_xyz_instrument_registry.json"
    )
    instruments = load_trade_xyz_registry(resolved_registry_path)
    active_trade_xyz = [
        instrument
        for instrument in instruments
        if instrument.venue.value == "trade_xyz" and instrument.active
    ]
    if symbols:
        requested = [item.strip().upper() for item in symbols.split(",") if item.strip()]
        available = {item.canonical_symbol.upper(): item for item in active_trade_xyz}
        missing = [item for item in requested if item not in available]
        if missing:
            raise ValueError(f"symbols not found in trade_xyz registry: {','.join(missing)}")
        active_trade_xyz = [available[item] for item in requested]
    if max_symbols is not None:
        active_trade_xyz = active_trade_xyz[:max_symbols]
    if not active_trade_xyz:
        raise ValueError("no active trade_xyz instruments found in registry")
    return resolved_registry_path, active_trade_xyz


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


def _csv_items(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _csv_intervals(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


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
            _resolved_registry_path, active_trade_xyz = _resolve_active_trade_xyz_instruments(
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

        with TradeXyzClient() as client:
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
            with TradeXyzClient() as client:
                resolved_registry_path = _refresh_trade_xyz_registry(
                    data_dir=settings.data_dir,
                    seed_path=seed_path,
                    client=client,
                )

        try:
            resolved_registry_path, active_trade_xyz = _resolve_active_trade_xyz_instruments(
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
                f"period_days={effective_signal_candle_period_days}"
            )
            if account_fee_user_address:
                typer.echo("account_fee_collection=enabled")
            return

        with TradeXyzClient() as client:
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

    @app.command("build-trade-xyz-quote-coverage")
    def build_trade_xyz_quote_coverage_cmd(
        raw_quotes_root: Path | None = typer.Option(
            None,
            "--raw-quotes-root",
            help="Raw quotes root containing trade_xyz/*.jsonl.",
        ),
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        min_days: float = typer.Option(30.0, "--min-days"),
        max_gap_minutes: float = typer.Option(10.0, "--max-gap-minutes"),
        traceable_only: bool = typer.Option(
            True,
            "--traceable-only/--include-untraceable",
            help="Evaluate coverage with rows that have raw_payload_ref; report excluded old rows.",
        ),
    ) -> None:
        settings = get_settings()
        requested_symbols = (
            [item.strip().upper() for item in symbols.split(",") if item.strip()]
            if symbols
            else None
        )
        try:
            manifest = build_trade_xyz_quote_coverage_manifest(
                data_dir=settings.data_dir,
                raw_quotes_root=raw_quotes_root,
                symbols=requested_symbols,
                min_days=min_days,
                max_gap_minutes=max_gap_minutes,
                traceable_only=traceable_only,
            )
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_quote_coverage_manifest.json'}"
        )
        typer.echo(f"coverage_passed={manifest['coverage_passed']}")
        typer.echo(f"traceable_only={manifest['traceable_only']}")
        typer.echo(
            "excluded_missing_raw_payload_ref_count="
            f"{manifest['excluded_missing_raw_payload_ref_count']}"
        )
        typer.echo(f"symbol_count={manifest['symbol_count']}")
        typer.echo(f"row_count={manifest['row_count']}")
        for symbol, item in manifest["per_symbol"].items():
            typer.echo(
                f"symbol={symbol} coverage_status={item['coverage_status']} "
                f"span_days={item['span_days']:.6f} max_gap_seconds={item['max_gap_seconds']}"
            )

    @app.command("build-trade-xyz-reference-data")
    def build_trade_xyz_reference_data_cmd(
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
            manifest = build_trade_xyz_reference_datasets(
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

        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_reference_datasets_manifest.json'}"
        )
        for name, path in manifest["artifacts"].items():
            typer.echo(f"{name}_path={path}")
        for name, count in manifest["row_counts"].items():
            typer.echo(f"{name}_count={count}")

    @app.command("collect-trade-xyz-real-market-reference")
    def collect_trade_xyz_real_market_reference_cmd(
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        symbols: str | None = typer.Option(
            None,
            "--symbols",
            help="Comma-separated Trade[XYZ] canonical symbols to map via real_market_symbol.",
        ),
        extra_symbols: str | None = typer.Option(
            None,
            "--extra-symbols",
            help="Comma-separated extra real-market symbols, e.g. ^VIX,UUP.",
        ),
        include_regime_symbols: bool = typer.Option(
            True,
            "--include-regime-symbols/--no-regime-symbols",
            help="Include default regime references such as ^VIX, UUP, USDJPY=X.",
        ),
        interval: str = typer.Option("1d", "--interval"),
        start: str | None = typer.Option(None, "--start", help="YYYY-MM-DD."),
        end: str | None = typer.Option(None, "--end", help="YYYY-MM-DD, exclusive."),
        period_days: int = typer.Option(365, "--period-days"),
    ) -> None:
        settings = get_settings()
        requested_symbols = (
            [item.strip().upper() for item in symbols.split(",") if item.strip()]
            if symbols
            else None
        )
        requested_extra_symbols = (
            [item.strip().upper() for item in extra_symbols.split(",") if item.strip()]
            if extra_symbols
            else None
        )
        try:
            manifest = collect_trade_xyz_real_market_reference(
                data_dir=settings.data_dir,
                registry_path=registry_path,
                symbols=requested_symbols,
                extra_symbols=requested_extra_symbols,
                include_regime_symbols=include_regime_symbols,
                interval=interval,
                start=date.fromisoformat(start) if start else None,
                end=date.fromisoformat(end) if end else None,
                period_days=period_days,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_real_market_reference_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"provider={manifest['provider']}")
        typer.echo(f"interval={manifest['interval']}")
        typer.echo(f"row_count={manifest['row_count']}")
        typer.echo(f"missing_mapped_symbols={','.join(manifest['missing_mapped_symbols'])}")
        typer.echo(
            f"normalized_reference_bars={manifest['artifacts']['normalized_reference_bars']}"
        )

    @app.command("collect-trade-xyz-signal-candles")
    def collect_trade_xyz_signal_candles_cmd(
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        intervals: str = typer.Option("30m,4h,1d,3d", "--intervals"),
        start: str | None = typer.Option(None, "--start", help="UTC start date YYYY-MM-DD."),
        end: str | None = typer.Option(None, "--end", help="UTC end date YYYY-MM-DD."),
        period_days: int = typer.Option(365, "--period-days"),
        request_delay_seconds: float = typer.Option(0.25, "--request-delay-seconds"),
    ) -> None:
        settings = get_settings()
        requested_symbols = (
            [item.strip().upper() for item in symbols.split(",") if item.strip()]
            if symbols
            else None
        )
        requested_intervals = [item.strip() for item in intervals.split(",") if item.strip()]
        try:
            with TradeXyzClient() as client:
                manifest = collect_trade_xyz_signal_candles(
                    data_dir=settings.data_dir,
                    registry_path=registry_path,
                    symbols=requested_symbols,
                    intervals=requested_intervals,
                    start=(
                        datetime.combine(date.fromisoformat(start), datetime.min.time(), tzinfo=UTC)
                        if start
                        else None
                    ),
                    end=(
                        datetime.combine(date.fromisoformat(end), datetime.min.time(), tzinfo=UTC)
                        if end
                        else None
                    ),
                    period_days=period_days,
                    request_delay_seconds=request_delay_seconds,
                    client=client,
                )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_signal_candles_manifest.json'}"
        )
        typer.echo(f"row_count={manifest['row_count']}")
        typer.echo(f"symbol_count={manifest['symbol_count']}")
        typer.echo(f"request_error_count={manifest['request_error_count']}")
        typer.echo(
            f"normalized_signal_candles={manifest['artifacts']['normalized_signal_candles']}"
        )

    @app.command("collect-trade-xyz-account-fee")
    def collect_trade_xyz_account_fee_cmd(
        user_address: str = typer.Option(
            ...,
            "--user-address",
            help="Public Hyperliquid user address for read-only userFees lookup.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            with TradeXyzClient() as client:
                manifest = collect_trade_xyz_account_fee_snapshot(
                    data_dir=settings.data_dir,
                    user_address=user_address,
                    client=client,
                )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            f"manifest_path={settings.data_dir / 'manifests/trade_xyz_account_fee_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"user_taker_fee_bps={manifest['parsed']['user_taker_fee_bps']}")
        typer.echo(f"user_maker_fee_bps={manifest['parsed']['user_maker_fee_bps']}")
        typer.echo(f"raw_artifact_path={manifest['raw_artifact_path']}")

    @app.command("collect-trade-xyz-historical-l2-archive")
    def collect_trade_xyz_historical_l2_archive_cmd(
        coin: str = typer.Option(
            ...,
            "--coin",
            help="Hyperliquid archive coin name. For HIP-3, use the exact archive coin name if different from UI symbol.",
        ),
        archive_date: str = typer.Option(..., "--date", help="UTC archive date, YYYY-MM-DD."),
        hour: int = typer.Option(..., "--hour", help="UTC archive hour, 0-23."),
        acknowledge_requester_pays: bool = typer.Option(
            False,
            "--acknowledge-requester-pays",
            help="Required for non-dry-run download because Hyperliquid archive transfer can cost money.",
        ),
        decompress: bool = typer.Option(True, "--decompress/--no-decompress"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--execute",
            help="Plan the requester-pays S3 download by default. Use --execute to download.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            parsed_archive_date = date.fromisoformat(archive_date)
            manifest = collect_hyperliquid_historical_l2_archive(
                data_dir=settings.data_dir,
                request=HistoricalL2ArchiveRequest(
                    coin=coin,
                    date=parsed_archive_date,
                    hour=hour,
                ),
                acknowledge_requester_pays=acknowledge_requester_pays,
                decompress=decompress,
                dry_run=dry_run,
            )
        except (ValueError, RuntimeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_l2_archive_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"source={manifest['source']}")
        typer.echo(f"s3_uri={manifest['s3_uri']}")
        typer.echo(f"aws_available={manifest['aws_available']}")
        typer.echo(f"raw_lz4_path={manifest['raw_lz4_path']}")
        if manifest["decompressed_path"] is not None:
            typer.echo(f"decompressed_path={manifest['decompressed_path']}")

    @app.command("collect-trade-xyz-historical-asset-ctxs-archive")
    def collect_trade_xyz_historical_asset_ctxs_archive_cmd(
        archive_date: str = typer.Option(..., "--date", help="UTC archive date, YYYY-MM-DD."),
        acknowledge_requester_pays: bool = typer.Option(
            False,
            "--acknowledge-requester-pays",
            help="Required for non-dry-run download because Hyperliquid archive transfer can cost money.",
        ),
        decompress: bool = typer.Option(True, "--decompress/--no-decompress"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--execute",
            help="Plan the requester-pays S3 download by default. Use --execute to download.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            manifest = collect_hyperliquid_historical_asset_ctxs_archive(
                data_dir=settings.data_dir,
                archive_date=date.fromisoformat(archive_date),
                acknowledge_requester_pays=acknowledge_requester_pays,
                decompress=decompress,
                dry_run=dry_run,
            )
        except (ValueError, RuntimeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"source={manifest['source']}")
        typer.echo(f"s3_uri={manifest['s3_uri']}")
        typer.echo(f"aws_available={manifest['aws_available']}")
        typer.echo(f"raw_lz4_path={manifest['raw_lz4_path']}")
        if manifest["decompressed_path"] is not None:
            typer.echo(f"decompressed_path={manifest['decompressed_path']}")

    @app.command("normalize-trade-xyz-historical-archive-quotes")
    def normalize_trade_xyz_historical_archive_quotes_cmd(
        l2_jsonl_path: Path = typer.Option(
            ...,
            "--l2-jsonl-path",
            help="Decompressed historical l2Book JSONL archive file.",
        ),
        asset_ctxs_path: Path | None = typer.Option(
            None,
            "--asset-ctxs-path",
            help="Optional decompressed historical asset_ctxs CSV/JSON file for mark/oracle/funding context.",
        ),
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        canonical_symbol: str | None = typer.Option(
            None,
            "--symbol",
            help="Canonical Trade[XYZ] symbol. Required when --coin cannot resolve registry entry.",
        ),
        coin: str | None = typer.Option(None, "--coin", help="Archive coin name."),
        output_path: Path | None = typer.Option(None, "--output-path"),
        normalize: bool = typer.Option(
            False,
            "--normalize/--no-normalize",
            help="Also rebuild data/normalized/quotes.parquet after writing raw quote rows.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            manifest = normalize_historical_archive_to_trade_xyz_quotes(
                data_dir=settings.data_dir,
                l2_jsonl_path=l2_jsonl_path,
                registry_path=registry_path,
                asset_ctxs_path=asset_ctxs_path,
                canonical_symbol=canonical_symbol,
                coin=coin,
                output_path=output_path,
                normalize=normalize,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_quote_normalization_manifest.json'}"
        )
        typer.echo(f"rows_written={manifest['rows_written']}")
        typer.echo(f"asset_ctx_matched={manifest['asset_ctx_matched']}")
        typer.echo(f"raw_quote_output_path={manifest['raw_quote_output_path']}")
        if manifest["normalized_quotes_path"] is not None:
            typer.echo(f"normalized_quotes_path={manifest['normalized_quotes_path']}")

    @app.command("plan-trade-xyz-historical-archive-bulk")
    def plan_trade_xyz_historical_archive_bulk_cmd(
        coins: str = typer.Option(..., "--coins", help="Comma-separated archive coin names."),
        start_date: str = typer.Option(..., "--start-date", help="UTC start date, YYYY-MM-DD."),
        end_date: str = typer.Option(..., "--end-date", help="UTC end date, YYYY-MM-DD."),
        hours: str | None = typer.Option(
            None,
            "--hours",
            help="Comma-separated UTC hours. Defaults to all 0-23.",
        ),
        include_asset_ctxs: bool = typer.Option(
            True,
            "--include-asset-ctxs/--no-asset-ctxs",
            help="Include daily asset_ctxs archive objects in the plan.",
        ),
    ) -> None:
        settings = get_settings()
        requested_coins = [item.strip() for item in coins.split(",") if item.strip()]
        requested_hours = (
            [int(item.strip()) for item in hours.split(",") if item.strip()]
            if hours is not None
            else None
        )
        try:
            manifest = build_hyperliquid_historical_archive_bulk_plan(
                data_dir=settings.data_dir,
                coins=requested_coins,
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date),
                hours=requested_hours,
                include_asset_ctxs=include_asset_ctxs,
            )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_bulk_plan_manifest.json'}"
        )
        typer.echo(f"date_count={manifest['date_count']}")
        typer.echo(f"estimated_l2_object_count={manifest['estimated_l2_object_count']}")
        typer.echo(
            f"estimated_asset_ctx_object_count={manifest['estimated_asset_ctx_object_count']}"
        )
        typer.echo(f"estimated_total_object_count={manifest['estimated_total_object_count']}")
        typer.echo("requester_pays_ack_required=True")

    @app.command("check-trade-xyz-historical-archive-preflight")
    def check_trade_xyz_historical_archive_preflight_cmd(
        fail_on_error: bool = typer.Option(False, "--fail-on-error"),
    ) -> None:
        settings = get_settings()
        manifest = check_hyperliquid_historical_archive_preflight(
            data_dir=settings.data_dir,
        )
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_preflight_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"return_code={manifest['return_code']}")
        typer.echo(f"aws_command_source={manifest['aws_command_source']}")
        typer.echo(f"preflight_command={shlex.join(manifest['preflight_command'])}")
        if manifest["stderr"]:
            typer.echo(f"stderr={manifest['stderr']}")
        if fail_on_error and manifest["status"] != "pass":
            raise typer.Exit(code=2)

    @app.command("execute-trade-xyz-historical-archive-bulk")
    def execute_trade_xyz_historical_archive_bulk_cmd(
        plan_path: Path | None = typer.Option(
            None,
            "--plan-path",
            help="Bulk plan manifest. Defaults to data/manifests/trade_xyz_historical_archive_bulk_plan_manifest.json.",
        ),
        acknowledge_requester_pays: bool = typer.Option(
            False,
            "--acknowledge-requester-pays",
            help="Required with --execute because Hyperliquid archive transfer can cost money.",
        ),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--execute",
            help="Preview selected downloads by default. Use --execute to run aws commands.",
        ),
        max_objects: int | None = typer.Option(
            None,
            "--max-objects",
            help="Limit selected objects so requester-pays downloads can be batched.",
        ),
        include_l2: bool = typer.Option(True, "--include-l2/--no-l2"),
        include_asset_ctxs: bool = typer.Option(True, "--include-asset-ctxs/--no-asset-ctxs"),
        skip_existing: bool = typer.Option(True, "--skip-existing/--include-existing"),
        decompress: bool = typer.Option(True, "--decompress/--no-decompress"),
    ) -> None:
        settings = get_settings()
        try:
            manifest = execute_hyperliquid_historical_archive_bulk_plan(
                data_dir=settings.data_dir,
                plan_path=plan_path,
                acknowledge_requester_pays=acknowledge_requester_pays,
                dry_run=dry_run,
                max_objects=max_objects,
                include_l2=include_l2,
                include_asset_ctxs=include_asset_ctxs,
                skip_existing=skip_existing,
                decompress=decompress,
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_bulk_execution_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"dry_run={manifest['dry_run']}")
        typer.echo(f"selected_object_count={manifest['selected_object_count']}")
        typer.echo(f"downloaded_object_count={manifest['downloaded_object_count']}")
        typer.echo(f"decompressed_object_count={manifest['decompressed_object_count']}")
        typer.echo(f"command_error_count={manifest['command_error_count']}")

    @app.command("normalize-trade-xyz-historical-archive-bulk")
    def normalize_trade_xyz_historical_archive_bulk_cmd(
        plan_path: Path | None = typer.Option(
            None,
            "--plan-path",
            help="Bulk plan manifest. Defaults to data/manifests/trade_xyz_historical_archive_bulk_plan_manifest.json.",
        ),
        registry_path: Path | None = typer.Option(
            None,
            "--registry-path",
            help="Instrument registry JSON written by `uv run sis probe trade-xyz`.",
        ),
        max_files: int | None = typer.Option(
            None,
            "--max-files",
            help="Limit decompressed l2Book files to normalize in this run.",
        ),
        skip_existing_raw_quotes: bool = typer.Option(
            True,
            "--skip-existing-raw-quotes/--overwrite-raw-quotes",
            help="Skip archive raw quote files that already exist.",
        ),
        normalize: bool = typer.Option(
            True,
            "--normalize/--no-normalize",
            help="Rebuild data/normalized/quotes.parquet after writing raw quote rows.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            manifest = normalize_historical_archive_bulk_to_trade_xyz_quotes(
                data_dir=settings.data_dir,
                plan_path=plan_path,
                registry_path=registry_path,
                max_files=max_files,
                skip_existing_raw_quotes=skip_existing_raw_quotes,
                normalize=normalize,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_historical_archive_bulk_quote_normalization_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"normalized_file_count={manifest['normalized_file_count']}")
        typer.echo(f"rows_written={manifest['rows_written']}")
        typer.echo(f"normalized_row_count={manifest['normalized_row_count']}")
        typer.echo(f"error_count={manifest['error_count']}")

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
        requested_symbols = (
            [item.strip().upper() for item in symbols.split(",") if item.strip()]
            if symbols
            else None
        )
        try:
            with TradeXyzClient() as client:
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

    @app.command("trade-xyz-collection-status")
    def trade_xyz_collection_status_cmd(
        raw_quotes_root: Path | None = typer.Option(
            None,
            "--raw-quotes-root",
            help="Raw quotes root containing trade_xyz/*.jsonl.",
        ),
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        min_days: float = typer.Option(30.0, "--min-days"),
        max_gap_minutes: float = typer.Option(10.0, "--max-gap-minutes"),
        traceable_only: bool = typer.Option(
            True,
            "--traceable-only/--include-untraceable",
            help="Evaluate quote coverage with rows that have raw_payload_ref.",
        ),
        refresh_coverage: bool = typer.Option(
            True,
            "--refresh-coverage/--no-refresh-coverage",
            help="Rebuild quote coverage from current raw quote files before writing status.",
        ),
        refresh_readiness: bool = typer.Option(
            True,
            "--refresh-readiness/--no-refresh-readiness",
            help="Rebuild data readiness from current manifests before writing status.",
        ),
        allow_known_gaps: bool = typer.Option(
            False,
            "--allow-known-gaps/--strict",
            help="Allow documented gaps that are out of pure-backtest scope.",
        ),
        duration_minutes: int = typer.Option(1440, "--duration-minutes"),
        interval_seconds: int = typer.Option(60, "--interval-seconds"),
        stale_after_minutes: float = typer.Option(180.0, "--stale-after-minutes"),
        fail_on_not_ready: bool = typer.Option(False, "--fail-on-not-ready"),
        fail_on_stale: bool = typer.Option(False, "--fail-on-stale"),
        fail_on_lock_stale: bool = typer.Option(False, "--fail-on-lock-stale"),
        fail_on_progress_warning: bool = typer.Option(False, "--fail-on-progress-warning"),
        fail_on_archive_preflight: bool = typer.Option(False, "--fail-on-archive-preflight"),
        fail_on_account_fee_missing: bool = typer.Option(False, "--fail-on-account-fee-missing"),
    ) -> None:
        settings = get_settings()
        requested_symbols = (
            [item.strip().upper() for item in symbols.split(",") if item.strip()]
            if symbols
            else None
        )
        manifest = build_trade_xyz_collection_status(
            data_dir=settings.data_dir,
            raw_quotes_root=raw_quotes_root,
            symbols=requested_symbols,
            min_days=min_days,
            max_gap_minutes=max_gap_minutes,
            traceable_only=traceable_only,
            refresh_coverage=refresh_coverage,
            refresh_readiness=refresh_readiness,
            allow_known_gaps=allow_known_gaps,
            duration_minutes=duration_minutes,
            interval_seconds=interval_seconds,
            stale_after_minutes=stale_after_minutes,
        )
        typer.echo(f"status_path={settings.data_dir / 'ops/trade_xyz_collection_status.json'}")
        typer.echo(f"report_path={manifest['report_path']}")
        typer.echo(f"decision={manifest['decision']}")
        typer.echo(f"backtest_data_ready={manifest['backtest_data_ready']}")
        typer.echo(f"readiness_decision={manifest['readiness_decision']}")
        typer.echo(f"fail_count={manifest['fail_count']}")
        typer.echo(f"known_gap_count={manifest['known_gap_count']}")
        typer.echo(f"failing_requirements={','.join(manifest['readiness_requirements']['fail'])}")
        typer.echo(
            f"known_gap_requirements={','.join(manifest['readiness_requirements']['known_gap'])}"
        )
        readiness_details = manifest["readiness_requirement_details"]
        funding_details = readiness_details.get("funding_events", {})
        oracle_details = readiness_details.get("oracle_timestamp_provenance", {})
        signal_details = readiness_details.get("signal_candles", {})
        typer.echo(f"funding_events_status={funding_details.get('status')}")
        typer.echo(f"funding_events_skipped={funding_details.get('skipped')}")
        typer.echo(f"oracle_timestamp_provenance_status={oracle_details.get('status')}")
        typer.echo(f"oracle_ts_missing_rate={oracle_details.get('oracle_ts_missing_rate')}")
        typer.echo(f"signal_candles_status={signal_details.get('status')}")
        typer.echo(
            "signal_candles_missing_symbols="
            f"{','.join(signal_details.get('missing_symbols') or [])}"
        )
        typer.echo(
            "signal_candles_missing_intervals="
            f"{','.join(signal_details.get('missing_intervals') or [])}"
        )
        typer.echo(
            f"signal_candles_request_error_count={signal_details.get('request_error_count')}"
        )
        typer.echo(f"latest_file_stale={manifest['latest_file_stale']}")
        typer.echo(f"collector_running={manifest['collector_process']['running']}")
        typer.echo(f"collector_process_count={manifest['collector_process']['process_count']}")
        typer.echo(f"supervisor_running={manifest['supervisor_process']['running']}")
        typer.echo(f"supervisor_process_count={manifest['supervisor_process']['process_count']}")
        typer.echo(f"cycle_lock_stale={manifest['locks']['cycle']['stale']}")
        typer.echo(f"supervisor_lock_stale={manifest['locks']['supervisor']['stale']}")
        typer.echo(f"aws_cli_available={manifest['runtime_prerequisites']['aws_cli']['available']}")
        typer.echo(f"aws_command_source={manifest['runtime_prerequisites']['aws_cli']['source']}")
        typer.echo(f"lz4_available={manifest['runtime_prerequisites']['lz4']['available']}")
        archive_artifacts = manifest["historical_archive_artifacts"]
        typer.echo(
            f"historical_archive_bulk_plan_exists={archive_artifacts['bulk_plan']['exists']}"
        )
        typer.echo(
            "historical_archive_bulk_plan_estimated_total_object_count="
            f"{archive_artifacts['bulk_plan']['estimated_total_object_count']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_status="
            f"{archive_artifacts['bulk_execution']['status']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_dry_run="
            f"{archive_artifacts['bulk_execution']['dry_run']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_selected_object_count="
            f"{archive_artifacts['bulk_execution']['selected_object_count']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_downloaded_object_count="
            f"{archive_artifacts['bulk_execution']['downloaded_object_count']}"
        )
        typer.echo(
            "historical_archive_bulk_execution_command_error_count="
            f"{archive_artifacts['bulk_execution']['command_error_count']}"
        )
        typer.echo(
            "historical_archive_bulk_normalization_status="
            f"{archive_artifacts['bulk_normalization']['status']}"
        )
        typer.echo(
            "historical_archive_bulk_normalization_normalized_file_count="
            f"{archive_artifacts['bulk_normalization']['normalized_file_count']}"
        )
        typer.echo(
            "account_fee_user_address_configured="
            f"{manifest['account_fee_prerequisites']['configured']}"
        )
        account_fee_artifact = manifest["account_fee_artifact"]
        typer.echo(f"account_fee_manifest_exists={account_fee_artifact['exists']}")
        typer.echo(f"account_fee_manifest_status={account_fee_artifact['status']}")
        typer.echo(
            "account_fee_manifest_user_matches_env="
            f"{account_fee_artifact['matches_configured_user']}"
        )
        typer.echo(f"account_fee_user_taker_fee_bps={account_fee_artifact['user_taker_fee_bps']}")
        typer.echo(f"account_fee_user_maker_fee_bps={account_fee_artifact['user_maker_fee_bps']}")
        typer.echo(f"progress_status={manifest['progress_since_previous_status']['status']}")
        typer.echo(
            f"latest_file_age_seconds={manifest['raw_quote_inventory']['latest_file_age_seconds']}"
        )
        typer.echo(
            "estimated_max_collection_days_required="
            f"{manifest['coverage']['estimated_max_collection_days_required']}"
        )
        typer.echo(
            f"coverage_completion_ratio_by_span={manifest['coverage']['completion_ratio_by_span']}"
        )
        if manifest["next_actions"]:
            typer.echo(f"next_command={manifest['next_actions'][0]['command']}")
            for index, action in enumerate(manifest["next_actions"], start=1):
                typer.echo(f"next_action_{index}_key={action.get('key')}")
                if action.get("status") is not None:
                    typer.echo(f"next_action_{index}_status={action.get('status')}")
                if action.get("blocked_by"):
                    typer.echo(
                        f"next_action_{index}_blocked_by={','.join(action.get('blocked_by', []))}"
                    )
                for command_key in (
                    "plan_command",
                    "preflight_command",
                    "preflight_status",
                    "preflight_return_code",
                    "dry_run_command",
                    "execute_command",
                    "command",
                    "follow_up_command",
                    "final_check_command",
                ):
                    command_value = action.get(command_key)
                    if command_value:
                        typer.echo(f"next_action_{index}_{command_key}={command_value}")
                if action.get("env_var"):
                    typer.echo(f"next_action_{index}_env_var={action.get('env_var')}")
                    typer.echo(f"next_action_{index}_env_configured={action.get('env_configured')}")
                if action.get("user_address_sha256"):
                    typer.echo(
                        f"next_action_{index}_user_address_sha256={action.get('user_address_sha256')}"
                    )
        if fail_on_lock_stale and (
            manifest["locks"]["cycle"]["stale"] or manifest["locks"]["supervisor"]["stale"]
        ):
            raise typer.Exit(code=2)
        if (
            fail_on_progress_warning
            and manifest["progress_since_previous_status"]["status"] == "warning"
        ):
            raise typer.Exit(code=2)
        if (
            fail_on_archive_preflight
            and manifest["historical_archive_preflight"]["status"] == "fail"
        ):
            raise typer.Exit(code=2)
        if fail_on_account_fee_missing and (
            "account_specific_fee" in manifest["readiness_requirements"]["known_gap"]
            or manifest["account_fee_artifact"]["exists"] is not True
            or manifest["account_fee_artifact"]["status"] != "pass"
            or manifest["account_fee_artifact"]["user_taker_fee_bps"] is None
            or manifest["account_fee_artifact"]["user_maker_fee_bps"] is None
            or manifest["account_fee_artifact"]["matches_configured_user"] is False
        ):
            raise typer.Exit(code=2)
        if fail_on_stale and manifest["latest_file_stale"]:
            raise typer.Exit(code=2)
        if fail_on_not_ready and not manifest["backtest_data_ready"]:
            raise typer.Exit(code=2)

    @app.command("build-trade-xyz-data-bundle")
    def build_trade_xyz_data_bundle_cmd(
        collection_config: Path = typer.Option(
            DEFAULT_COLLECTION_CONFIG_PATH,
            "--collection-config",
            help="Non-secret Trade[XYZ] data collection defaults.",
        ),
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
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        min_days: float | None = typer.Option(None, "--min-days"),
        max_gap_minutes: float | None = typer.Option(None, "--max-gap-minutes"),
        max_oracle_lag_minutes: float | None = typer.Option(None, "--max-oracle-lag-minutes"),
        traceable_only: bool = typer.Option(
            True,
            "--traceable-only/--include-untraceable",
            help="Evaluate quote coverage with rows that have raw_payload_ref.",
        ),
        funding_start_time_ms: int | None = typer.Option(None, "--funding-start-time-ms"),
        funding_end_time_ms: int | None = typer.Option(None, "--funding-end-time-ms"),
        auto_funding_window: bool = typer.Option(
            False,
            "--auto-funding-window/--no-auto-funding-window",
            help="Infer fundingHistory start/end from raw Trade[XYZ] quote timestamps.",
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
            help="Collect historical candleSnapshot OHLCV for signal inputs.",
        ),
        signal_candle_intervals: str | None = typer.Option(None, "--signal-candle-intervals"),
        signal_candle_period_days: int | None = typer.Option(None, "--signal-candle-period-days"),
        signal_candle_max_age_hours: float | None = typer.Option(
            None,
            "--signal-candle-max-age-hours",
            help="Reuse existing complete signal candle artifact when it is newer than this.",
        ),
        account_fee_user_address: str | None = typer.Option(
            None,
            "--account-fee-user-address",
            help="Public Hyperliquid user address for optional read-only userFees collection.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            config = load_trade_xyz_data_collection_config(collection_config)
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2) from exc
        requested_symbols = _csv_items(symbols) or list(config.symbols)
        effective_min_days = min_days if min_days is not None else config.min_days
        effective_max_gap_minutes = (
            max_gap_minutes if max_gap_minutes is not None else config.max_gap_minutes
        )
        effective_max_oracle_lag_minutes = (
            max_oracle_lag_minutes
            if max_oracle_lag_minutes is not None
            else config.max_oracle_lag_minutes
        )
        effective_signal_candle_intervals = _csv_intervals(signal_candle_intervals) or list(
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
        effective_usable_start_date = (
            date.fromisoformat(config.usable_start_date) if config.usable_start_date else None
        )
        if funding_start_time_ms is not None or auto_funding_window:
            with TradeXyzClient() as client:
                manifest = build_trade_xyz_data_collection_bundle(
                    data_dir=settings.data_dir,
                    registry_path=registry_path,
                    raw_quotes_root=raw_quotes_root,
                    symbols=requested_symbols,
                    min_days=effective_min_days,
                    max_gap_minutes=effective_max_gap_minutes,
                    traceable_only=traceable_only,
                    max_oracle_lag_minutes=effective_max_oracle_lag_minutes,
                    funding_start_time_ms=funding_start_time_ms,
                    funding_end_time_ms=funding_end_time_ms,
                    auto_funding_window=auto_funding_window,
                    funding_client=client,
                    account_fee_user_address=account_fee_user_address,
                    account_fee_client=client,
                    collect_signal_candles=collect_signal_candles,
                    signal_candle_intervals=effective_signal_candle_intervals,
                    signal_candle_period_days=effective_signal_candle_period_days,
                    signal_candle_max_age_hours=effective_signal_candle_max_age_hours,
                    signal_candle_client=client,
                    collect_real_market_reference_data=collect_real_market_reference_data,
                    usable_start_date=effective_usable_start_date,
                    allow_known_gaps=allow_known_gaps,
                )
        else:
            manifest = build_trade_xyz_data_collection_bundle(
                data_dir=settings.data_dir,
                registry_path=registry_path,
                raw_quotes_root=raw_quotes_root,
                symbols=requested_symbols,
                min_days=effective_min_days,
                max_gap_minutes=effective_max_gap_minutes,
                traceable_only=traceable_only,
                max_oracle_lag_minutes=effective_max_oracle_lag_minutes,
                funding_start_time_ms=funding_start_time_ms,
                funding_end_time_ms=funding_end_time_ms,
                auto_funding_window=auto_funding_window,
                account_fee_user_address=account_fee_user_address,
                collect_signal_candles=collect_signal_candles,
                signal_candle_intervals=effective_signal_candle_intervals,
                signal_candle_period_days=effective_signal_candle_period_days,
                signal_candle_max_age_hours=effective_signal_candle_max_age_hours,
                collect_real_market_reference_data=collect_real_market_reference_data,
                usable_start_date=effective_usable_start_date,
                allow_known_gaps=allow_known_gaps,
            )
        typer.echo(
            "manifest_path="
            f"{settings.data_dir / 'manifests/trade_xyz_data_collection_bundle_manifest.json'}"
        )
        typer.echo(f"status={manifest['status']}")
        typer.echo(f"readiness_decision={manifest['readiness_decision']}")
        typer.echo(f"backtest_data_ready={manifest['backtest_data_ready']}")
        typer.echo(f"failed_step_count={manifest['failed_step_count']}")
