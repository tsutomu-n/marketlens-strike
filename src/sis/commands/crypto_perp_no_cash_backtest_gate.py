from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from sis.crypto_perp.no_cash_backtest_gate import write_no_cash_backtest_gate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_no_cash_backtest_gate_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-no-cash-backtest-gate")
    def crypto_perp_no_cash_backtest_gate_cmd(
        decision: Path = typer.Option(..., "--decision"),
        data_availability: Path = typer.Option(..., "--data-availability"),
        backtest: Path = typer.Option(..., "--backtest"),
        stress: Path = typer.Option(..., "--stress"),
        rolling_stability: Path = typer.Option(..., "--rolling-stability"),
        out: Path = typer.Option(
            Path("data/crypto_perp/no_cash_backtest_gate/latest"),
            "--out",
            help="Output directory for the no-cash backtest gate artifact.",
        ),
    ) -> None:
        try:
            result = write_no_cash_backtest_gate(
                decision_path=decision,
                data_availability_path=data_availability,
                backtest_path=backtest,
                stress_path=stress,
                rolling_stability_path=rolling_stability,
                out_dir=out,
                created_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("network_attempted=false")
            typer.echo("exchange_write_used=false")
            typer.echo("live_order_submitted=false")
            typer.echo("actual_cash_used=false")
            typer.echo("paper_permission_granted=false")
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        status = "pass" if result.gate.gate_decision == "NO_CASH_BACKTEST_HOLD" else "blocked"
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("actual_cash_used=false")
        typer.echo("paper_permission_granted=false")
        typer.echo("permits_paper_order=false")
        typer.echo("permits_live_order=false")
        typer.echo("profit_proven=false")
        typer.echo(f"status={status}")
        typer.echo(f"gate_decision={result.gate.gate_decision}")
        typer.echo(f"blocker_count={len(result.gate.blockers)}")
        gate_path = result.paths["no_cash_backtest_gate.json"]
        gate_report = result.paths["no_cash_backtest_gate.md"]
        typer.echo(f"gate_path={gate_path.as_posix()}")
        typer.echo(f"gate_report={gate_report.as_posix()}")
