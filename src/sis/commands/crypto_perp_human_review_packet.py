from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from sis.crypto_perp.human_review_packet import write_human_review_packet


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def register_crypto_perp_human_review_packet_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-human-review-packet")
    def crypto_perp_human_review_packet_cmd(
        selection_manifest: Path = typer.Option(
            Path("data/crypto_perp/real_market_no_cash/ticker_required/selection_manifest.json"),
            "--selection-manifest",
        ),
        decision: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json"
            ),
            "--decision",
        ),
        tournament_rows: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/tournament_rows_v2.json"
            ),
            "--tournament-rows",
        ),
        bias_guard: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/bias_guard.json"
            ),
            "--bias-guard",
        ),
        data_availability: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/data_availability_ledger.json"
            ),
            "--data-availability",
        ),
        signal_rows: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/signal_rows.jsonl"
            ),
            "--signal-rows",
        ),
        backtest: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json"
            ),
            "--backtest",
        ),
        stress: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json"
            ),
            "--stress",
        ),
        rolling_stability: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/rolling_stability_result.json"
            ),
            "--rolling-stability",
        ),
        gate: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json"
            ),
            "--gate",
        ),
        kill_report: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json"
            ),
            "--kill-report",
        ),
        leaderboard: Path = typer.Option(
            Path(
                "data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest/candidate_leaderboard.json"
            ),
            "--leaderboard",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/real_market_no_cash/human_review_packet/latest"),
            "--out",
            help="Output directory for the human review packet artifact.",
        ),
    ) -> None:
        try:
            result = write_human_review_packet(
                selection_manifest_path=selection_manifest,
                decision_path=decision,
                tournament_rows_path=tournament_rows,
                bias_guard_path=bias_guard,
                data_availability_path=data_availability,
                signal_rows_path=signal_rows,
                backtest_path=backtest,
                stress_path=stress,
                rolling_stability_path=rolling_stability,
                gate_path=gate,
                kill_report_path=kill_report,
                leaderboard_path=leaderboard,
                out_dir=out,
                created_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo("paper_permission_granted=false")
            typer.echo("permits_paper_order=false")
            typer.echo("actual_cash_used=false")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        summary = result.payload["summary"]
        typer.echo("status=pass")
        typer.echo(f"packet_decision={result.payload['packet_decision']}")
        typer.echo(f"next_action={result.payload['next_action']}")
        typer.echo(f"review_input_count={summary['review_input_count']}")
        typer.echo(f"known_gap_count={summary['known_gap_count']}")
        typer.echo(f"gate_decision={summary['gate_decision']}")
        typer.echo(f"kill_decision={summary['kill_decision']}")
        typer.echo(f"top_next_action={summary['top_next_action']}")
        typer.echo("paper_permission_granted=false")
        typer.echo("permits_paper_order=false")
        typer.echo("permits_live_order=false")
        typer.echo("actual_cash_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("profit_proven=false")
        typer.echo(f"json_path={result.json_path.as_posix()}")
        typer.echo(f"markdown_path={result.markdown_path.as_posix()}")
