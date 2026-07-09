from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from sis.crypto_perp.no_trade_kill_report import write_no_trade_kill_report


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_no_trade_kill_report_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-no-trade-kill-report")
    def crypto_perp_no_trade_kill_report_cmd(
        signal_rows: Path = typer.Option(..., "--signal-rows"),
        backtest: Path = typer.Option(..., "--backtest"),
        stress: Path = typer.Option(..., "--stress"),
        tournament_rows: Path | None = typer.Option(None, "--tournament-rows"),
        out: Path = typer.Option(
            Path("data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest"),
            "--out",
            help="Output directory for the NO_TRADE kill report artifact.",
        ),
    ) -> None:
        try:
            result = write_no_trade_kill_report(
                signal_rows_path=signal_rows,
                backtest_path=backtest,
                stress_path=stress,
                tournament_rows_path=tournament_rows,
                out_dir=out,
                created_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo("permits_paper_order=false")
            typer.echo("actual_cash_used=false")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"kill_decision={result.payload['kill_decision']}")
        typer.echo(f"reason_code_count={len(result.payload['reason_codes'])}")
        typer.echo("paper_permission_granted=false")
        typer.echo("permits_paper_order=false")
        typer.echo("permits_live_order=false")
        typer.echo("actual_cash_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("profit_proven=false")
        typer.echo(f"json_path={result.json_path.as_posix()}")
        typer.echo(f"markdown_path={result.markdown_path.as_posix()}")
