from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable

import typer

from sis.settings import get_settings
from sis.venues.trade_xyz.account_fee import collect_trade_xyz_account_fee_snapshot
from sis.venues.trade_xyz.candles import DEFAULT_SIGNAL_CANDLE_REQUEST_DELAY_SECONDS
from sis.venues.trade_xyz.candles import collect_trade_xyz_signal_candles
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.coverage import build_trade_xyz_quote_coverage_manifest
from sis.venues.trade_xyz.reference_data import build_trade_xyz_reference_datasets
from sis.venues.trade_xyz.real_market_reference import collect_trade_xyz_real_market_reference


def register_quote_reference_commands(
    app: typer.Typer,
    *,
    trade_xyz_client_factory: Callable[[], TradeXyzClient] = TradeXyzClient,
) -> None:
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
        providers: str = typer.Option(
            "yfinance,yahooquery,stooq",
            "--providers",
            help="Comma-separated provider chain for unresolved symbols.",
        ),
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
        requested_providers = [item.strip() for item in providers.split(",") if item.strip()]
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
                provider_names=requested_providers,
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
        typer.echo(f"provider_chain={','.join(str(item) for item in manifest['provider_chain'])}")
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
        request_delay_seconds: float = typer.Option(
            DEFAULT_SIGNAL_CANDLE_REQUEST_DELAY_SECONDS, "--request-delay-seconds"
        ),
    ) -> None:
        settings = get_settings()
        requested_symbols = (
            [item.strip().upper() for item in symbols.split(",") if item.strip()]
            if symbols
            else None
        )
        requested_intervals = [item.strip() for item in intervals.split(",") if item.strip()]
        try:
            with trade_xyz_client_factory() as client:
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
            with trade_xyz_client_factory() as client:
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
