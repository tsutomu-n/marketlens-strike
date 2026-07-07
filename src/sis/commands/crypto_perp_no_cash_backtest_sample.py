from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import typer

from sis.crypto_perp.no_cash_backtest_sample import write_no_cash_backtest_sample


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_no_cash_backtest_sample_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-no-cash-backtest-sample")
    def crypto_perp_no_cash_backtest_sample_cmd(
        data_dir: Path = typer.Option(Path("data/crypto_perp"), "--data-dir"),
        out: Path = typer.Option(
            Path("data/crypto_perp/000_no_cash_backtest_sample/latest"),
            "--out",
            help="Output directory for no-cash dogfood sample artifacts.",
        ),
        target_event_count: int = typer.Option(30, "--target-event-count", min=1),
        min_events_for_stability: int = typer.Option(
            30,
            "--min-events-for-stability",
            min=1,
        ),
        fold_count: int = typer.Option(2, "--fold-count", min=2),
        notional_usd: str = typer.Option("100", "--notional-usd"),
    ) -> None:
        try:
            result = write_no_cash_backtest_sample(
                data_dir=data_dir,
                out_dir=out,
                created_at=_utc_now(),
                target_event_count=target_event_count,
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
        typer.echo("fixture_only=true")
        typer.echo("real_market_evidence_claimed=false")
        typer.echo("status=pass")
        typer.echo(f"event_count={result.event_count}")
        typer.echo(f"outcome_count={result.outcome_count}")
        typer.echo(f"generated_event_count={result.generated_event_count}")
        typer.echo(f"source_availability_count={result.source_availability_count}")
        typer.echo(f"rows_path={result.rows_path.as_posix()}")
        typer.echo(f"guard_path={result.guard_path.as_posix()}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")
