from __future__ import annotations

from datetime import date
from pathlib import Path
import subprocess
from typing import Callable

import typer
from loguru import logger

from sis.models import InstrumentSpec
from sis.settings import get_settings
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import normalize_quotes
from sis.storage.normalize import normalize_trade_xyz_ws_quotes
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import join_csv
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.collector import collect_trade_xyz_quote_window
from sis.venues.trade_xyz.data_bundle import build_trade_xyz_data_collection_bundle
from sis.venues.trade_xyz.registry import build_trade_xyz_registry
from sis.venues.trade_xyz.registry import load_trade_xyz_registry
from sis.venues.trade_xyz.registry import write_trade_xyz_registry
from sis.venues.trade_xyz.rest_parity import build_trade_xyz_rest_parity_manifest
from sis.venues.trade_xyz.ws_envelope import SUPPORTED_WS_SUBSCRIPTIONS
from sis.venues.trade_xyz.ws_quality import build_trade_xyz_ws_quality_manifest
from sis.venues.trade_xyz.ws_recorder import run_trade_xyz_ws_capture
from sis.venues.trade_xyz.ws_recorder import WsCaptureConfig
from sis.venues.trade_xyz.ws_recorder import WsSubscriptionTarget


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


def register_quote_collection_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
    *,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
) -> None:
    @app.command("collect-trade-xyz-ws")
    def collect_trade_xyz_ws_cmd(
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
        symbols: str | None = typer.Option(None, "--symbols", help="Comma-separated symbols."),
        max_symbols: int | None = typer.Option(None, "--max-symbols"),
        subscriptions: str | None = typer.Option(
            None,
            "--subscriptions",
            help="Comma-separated subscriptions. Supported: bbo,trades,activeAssetCtx,l2Book,allMids.",
        ),
        ws_url: str | None = typer.Option(None, "--ws-url"),
        duration_minutes: int | None = typer.Option(None, "--duration-minutes"),
        heartbeat_seconds: int | None = typer.Option(None, "--heartbeat-seconds"),
        output_dir: Path | None = typer.Option(None, "--output-dir"),
        write_control_messages: bool = typer.Option(
            True,
            "--write-control-messages/--drop-control-messages",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
    ) -> None:
        settings = get_settings()
        config = load_trade_xyz_data_collection_config(collection_config)
        requested_subscriptions = (
            [item.strip() for item in subscriptions.split(",") if item.strip()]
            if subscriptions
            else list(config.ws_default_subscriptions)
        )
        invalid_subscriptions = [
            item for item in requested_subscriptions if item not in SUPPORTED_WS_SUBSCRIPTIONS
        ]
        if invalid_subscriptions:
            typer.echo("unsupported subscriptions: " + ",".join(invalid_subscriptions))
            raise typer.Exit(code=2)
        resolved_registry_path, active_trade_xyz = _resolve_active_trade_xyz_instruments(
            data_dir=settings.data_dir,
            registry_path=registry_path,
            symbols=symbols,
            max_symbols=max_symbols,
        )
        targets: list[WsSubscriptionTarget] = []
        for subscription_name in requested_subscriptions:
            if subscription_name == "allMids":
                targets.append(WsSubscriptionTarget(subscription=subscription_name))
                continue
            for instrument in active_trade_xyz:
                coin = instrument.coin or f"xyz:{instrument.canonical_symbol}"
                targets.append(
                    WsSubscriptionTarget(
                        subscription=subscription_name,
                        canonical_symbol=instrument.canonical_symbol,
                        coin=coin,
                    )
                )
        effective_output_dir = output_dir or (settings.data_dir / config.ws_output_root)
        effective_duration_minutes = duration_minutes or config.ws_duration_minutes
        effective_heartbeat_seconds = heartbeat_seconds or config.ws_heartbeat_seconds
        effective_ws_url = ws_url or config.ws_url
        capture_config = WsCaptureConfig(
            ws_url=effective_ws_url,
            dex="xyz",
            output_root=effective_output_dir,
            duration_seconds=max(1, effective_duration_minutes * 60),
            heartbeat_seconds=effective_heartbeat_seconds,
            reconnect_max_attempts=config.ws_reconnect_max_attempts,
            reconnect_initial_delay_seconds=config.ws_reconnect_initial_delay_seconds,
            reconnect_max_delay_seconds=config.ws_reconnect_max_delay_seconds,
            write_control_messages=write_control_messages and config.ws_write_control_messages,
            dry_run=dry_run,
        )
        if dry_run:
            typer.echo("dry_run=true")
            typer.echo(f"registry_path={resolved_registry_path}")
            typer.echo(f"symbols={','.join(item.canonical_symbol for item in active_trade_xyz)}")
            typer.echo(f"subscriptions={','.join(requested_subscriptions)}")
            typer.echo(f"ws_url={effective_ws_url}")
            typer.echo(f"heartbeat_seconds={effective_heartbeat_seconds}")
            typer.echo(f"duration_minutes={effective_duration_minutes}")
            typer.echo(f"output_dir={effective_output_dir}")
            return
        manifest = run_trade_xyz_ws_capture(config=capture_config, targets=targets)
        git_head = None
        try:
            git_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
            ).strip()
        except Exception:
            git_head = None
        manifest["command"] = "collect-trade-xyz-ws"
        manifest["registry_path"] = str(resolved_registry_path)
        manifest["git_head"] = git_head
        write_json(
            settings.data_dir / "manifests/trade_xyz_ws_capture_manifest.json",
            manifest,
        )
        typer.echo(
            f"manifest_path={settings.data_dir / 'manifests/trade_xyz_ws_capture_manifest.json'}"
        )
        typer.echo(f"row_count={manifest['row_count']}")
        typer.echo(f"reconnect_count={manifest['reconnect_count']}")
        typer.echo(f"error_count={manifest['error_count']}")

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
