from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import typer

from sis.crypto_perp.backtest_candidate_pack import build_crypto_perp_backtest_candidate_pack


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_backtest_candidate_pack_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-backtest-candidate-pack")
    def crypto_perp_backtest_candidate_pack_cmd(
        data_dir: Path = typer.Option(Path("data/crypto_perp"), "--data-dir"),
        out: Path = typer.Option(
            Path("data/crypto_perp/backtest_candidate_pack/latest"),
            "--out",
            help="Output directory for the Crypto Perp backtest candidate pack.",
        ),
        notional_usd: str = typer.Option("100", "--notional-usd"),
        min_events: int = typer.Option(10, "--min-events", min=1),
        min_events_for_stability: int = typer.Option(
            30,
            "--min-events-for-stability",
            min=1,
        ),
        fold_count: int = typer.Option(0, "--fold-count", min=0),
        fee_rate: str = typer.Option("0.0006", "--fee-rate"),
        funding_rate: str = typer.Option("0.0001", "--funding-rate"),
        slippage_bps: str = typer.Option("2", "--slippage-bps"),
        max_holding_minutes: int = typer.Option(60, "--max-holding-minutes", min=1),
    ) -> None:
        try:
            result = build_crypto_perp_backtest_candidate_pack(
                data_dir=data_dir,
                out_dir=out,
                created_at=_utc_now(),
                notional_usd=Decimal(notional_usd),
                min_events=min_events,
                min_events_for_stability=min_events_for_stability,
                fold_count=fold_count,
                fee_rate=Decimal(fee_rate),
                funding_rate=Decimal(funding_rate),
                slippage_bps=Decimal(slippage_bps),
                max_holding_minutes=max_holding_minutes,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("network_attempted=false")
        typer.echo("external_api_called=false")
        typer.echo("wallet_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("permits_live_order=false")
        typer.echo("profit_proven=false")
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision.decision}")
        typer.echo(f"reason_code_count={len(result.decision.reason_codes)}")
        typer.echo(f"event_count={result.decision.event_count}")
        typer.echo(f"outcome_count={result.decision.outcome_count}")
        typer.echo(f"decision_path={result.paths['decision.json'].as_posix()}")
        typer.echo(f"decision_report={result.paths['decision.md'].as_posix()}")
