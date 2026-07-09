from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from sis.crypto_perp.candidate_leaderboard import write_candidate_leaderboard


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_candidate_leaderboard_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-candidate-leaderboard")
    def crypto_perp_candidate_leaderboard_cmd(
        decision: Path = typer.Option(..., "--decision"),
        backtest: Path = typer.Option(..., "--backtest"),
        stress: Path = typer.Option(..., "--stress"),
        kill_report: Path = typer.Option(..., "--kill-report"),
        gate: Path = typer.Option(..., "--gate"),
        signal_rows: Path | None = typer.Option(None, "--signal-rows"),
        out: Path = typer.Option(
            Path("data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest"),
            "--out",
            help="Output directory for the candidate leaderboard artifact.",
        ),
    ) -> None:
        try:
            result = write_candidate_leaderboard(
                decision_path=decision,
                backtest_path=backtest,
                stress_path=stress,
                kill_report_path=kill_report,
                gate_path=gate,
                signal_rows_path=signal_rows,
                out_dir=out,
                created_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo("permits_paper_order=false")
            typer.echo("actual_cash_used=false")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        summary = result.payload["summary"]
        top = result.payload["rows"][0]
        typer.echo("status=pass")
        typer.echo(f"row_count={summary['row_count']}")
        typer.echo(f"top_next_action={summary['top_next_action']}")
        typer.echo(f"top_candidate_id={summary['top_candidate_id']}")
        typer.echo(f"top_kill_decision={summary['top_kill_decision']}")
        typer.echo(f"top_ranking_score={top['ranking_score']}")
        typer.echo("paper_permission_granted=false")
        typer.echo("permits_paper_order=false")
        typer.echo("permits_live_order=false")
        typer.echo("actual_cash_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("profit_proven=false")
        typer.echo(f"json_path={result.json_path.as_posix()}")
        typer.echo(f"markdown_path={result.markdown_path.as_posix()}")
