from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

import typer

from sis.settings import get_settings
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.data_bundle import build_trade_xyz_data_collection_bundle


def _csv_items(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _csv_intervals(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def register_quote_data_bundle_commands(
    app: typer.Typer,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
) -> None:
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
        effective_signal_candle_request_delay_seconds = (
            signal_candle_request_delay_seconds
            if signal_candle_request_delay_seconds is not None
            else config.signal_candle_request_delay_seconds
        )
        effective_usable_start_date = (
            date.fromisoformat(config.usable_start_date) if config.usable_start_date else None
        )
        if funding_start_time_ms is not None or auto_funding_window:
            with trade_xyz_client_factory() as client:
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
                    signal_candle_request_delay_seconds=effective_signal_candle_request_delay_seconds,
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
                signal_candle_request_delay_seconds=effective_signal_candle_request_delay_seconds,
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
