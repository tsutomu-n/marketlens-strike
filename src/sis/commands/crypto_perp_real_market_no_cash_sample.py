from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import typer

from sis.crypto_perp.real_market_no_cash_sample import write_real_market_no_cash_sample


DEFAULT_PUBLIC_SOURCE_ROOT = Path(
    "data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_real_market_no_cash_sample_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-real-market-no-cash-sample")
    def crypto_perp_real_market_no_cash_sample_cmd(
        source_root: Path | None = typer.Option(
            None,
            "--source-root",
            help="Bitget public source_root produced by strategy-idea-candidates-bitget-source-refresh.",
        ),
        input_csv: Path | None = typer.Option(
            None,
            "--input-csv",
            help="Validated public candle CSV with ts, available_at, symbol, OHLC, and quote volume.",
        ),
        symbol: str = typer.Option("BTCUSDT", "--symbol"),
        out: Path = typer.Option(
            Path("data/crypto_perp/real_market_no_cash/latest"),
            "--out",
            help="Output directory for real-market no-cash local artifacts.",
        ),
        ticker_source_root: Path | None = typer.Option(
            None,
            "--ticker-source-root",
            help="Optional local source_root containing data/ticker_rows parquet artifacts. Defaults to --source-root when provided.",
        ),
        ticker_max_staleness_seconds: int = typer.Option(
            900,
            "--ticker-max-staleness-seconds",
            min=0,
            help="Maximum allowed ticker staleness at event cutoff.",
        ),
        target_event_count: int = typer.Option(30, "--target-event-count", min=1),
        lookback_minutes: int = typer.Option(60, "--lookback-minutes", min=1),
        horizon_minutes: int = typer.Option(60, "--horizon-minutes", min=1),
        interval_minutes: int = typer.Option(5, "--interval-minutes", min=1),
        min_events_for_stability: int = typer.Option(
            30,
            "--min-events-for-stability",
            min=1,
        ),
        fold_count: int = typer.Option(2, "--fold-count", min=2),
        notional_usd: str = typer.Option("100", "--notional-usd"),
    ) -> None:
        try:
            result = write_real_market_no_cash_sample(
                out_dir=out,
                created_at=_utc_now(),
                symbol=symbol,
                source_root=(
                    source_root
                    if source_root is not None or input_csv is not None
                    else DEFAULT_PUBLIC_SOURCE_ROOT
                ),
                input_csv=input_csv,
                ticker_source_root=ticker_source_root,
                ticker_max_staleness_seconds=ticker_max_staleness_seconds,
                target_event_count=target_event_count,
                lookback_minutes=lookback_minutes,
                horizon_minutes=horizon_minutes,
                interval_minutes=interval_minutes,
                min_events_for_stability=min_events_for_stability,
                fold_count=fold_count,
                notional_usd=Decimal(notional_usd),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("network_attempted=false")
        typer.echo("external_api_called=false")
        typer.echo("credentialed_exchange_api_used=false")
        typer.echo("paper_order_created=false")
        typer.echo("actual_cash_used=false")
        typer.echo("wallet_used=false")
        typer.echo("signing_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("profit_proven=false")
        typer.echo("fixture_only=false")
        typer.echo("real_market_public_source_used=true")
        typer.echo("paper_permission_granted=false")
        typer.echo("status=pass")
        typer.echo(f"event_count={result.event_count}")
        typer.echo(f"outcome_count={result.outcome_count}")
        typer.echo(f"source_availability_count={result.source_availability_count}")
        typer.echo(f"ticker_available_count={result.ticker_available_count}")
        typer.echo(f"funding_available_count={result.funding_available_count}")
        typer.echo(f"input_csv_path={result.input_csv_path.as_posix()}")
        typer.echo(f"rows_path={result.rows_path.as_posix()}")
        typer.echo(f"guard_path={result.guard_path.as_posix()}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")
