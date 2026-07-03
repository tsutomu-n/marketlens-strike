from __future__ import annotations

from pathlib import Path

import typer

from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.profit_core_reality_check import build_profit_core_reality_check
from sis.profit_core_reality_check.readers import RealityCheckReadError
from sis.profit_core_reality_check.rendering import render_profit_core_reality_check_markdown


def register_profit_core_reality_check_commands(app: typer.Typer) -> None:
    @app.command("profit-core-reality-check")
    def profit_core_reality_check_cmd(
        candidate_set: Path = typer.Option(
            ...,
            "--candidate-set",
            dir_okay=False,
            help="strategy_idea_candidate_set.v1 JSON artifact path.",
        ),
        search_ledger: Path = typer.Option(
            ...,
            "--search-ledger",
            dir_okay=False,
            help="Candidate search ledger JSONL path.",
        ),
        export_manifest: Path | None = typer.Option(
            None,
            "--export-manifest",
            dir_okay=False,
            help="Optional strategy_idea_candidate_export_manifest.v1 JSON path.",
        ),
        authoring_bridge: Path | None = typer.Option(
            None,
            "--authoring-bridge",
            dir_okay=False,
            help="Optional strategy_idea_candidate_authoring_bridge_manifest JSON path.",
        ),
        profit_readiness_inventory: Path | None = typer.Option(
            None,
            "--profit-readiness-inventory",
            dir_okay=False,
            help="Optional crypto_perp profit readiness inventory JSON path.",
        ),
        source_availability: Path | None = typer.Option(
            None,
            "--source-availability",
            dir_okay=False,
            help="Optional crypto_perp source availability JSON path.",
        ),
        risk_review: Path | None = typer.Option(
            None,
            "--risk-review",
            dir_okay=False,
            help="Optional crypto_perp risk taker review JSON path.",
        ),
        actual_cash_rows_summary: Path | None = typer.Option(
            None,
            "--actual-cash-rows-summary",
            dir_okay=False,
            help="Optional actual cash rows summary JSON path.",
        ),
        actual_cash_report_gate: Path | None = typer.Option(
            None,
            "--actual-cash-report-gate",
            dir_okay=False,
            help="Optional actual cash report gate run JSON path.",
        ),
        out: Path = typer.Option(
            Path("data/profit_core_reality_check/latest"),
            "--out",
            help="Output directory for profit core reality check artifacts.",
        ),
    ) -> None:
        try:
            check = build_profit_core_reality_check(
                candidate_set_path=candidate_set,
                search_ledger_path=search_ledger,
                export_manifest_path=export_manifest,
                authoring_bridge_path=authoring_bridge,
                profit_readiness_inventory_path=profit_readiness_inventory,
                source_availability_path=source_availability,
                risk_review_path=risk_review,
                actual_cash_rows_summary_path=actual_cash_rows_summary,
                actual_cash_report_gate_path=actual_cash_report_gate,
            )
        except (OSError, RealityCheckReadError, ValueError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "profit_core_reality_check.json"
        report_path = out / "profit_core_reality_check.md"
        write_json_artifact(json_path, check.model_dump(mode="json"))
        write_text_artifact(report_path, render_profit_core_reality_check_markdown(check))
        typer.echo("network_attempted=false")
        typer.echo("credentials_used=false")
        typer.echo("exchange_write_used=false")
        typer.echo("production_exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("permits_live_order=false")
        typer.echo(f"status={check.summary.overall_status.lower()}")
        typer.echo(f"next_single_blocker_to_fix={check.next_single_blocker_to_fix}")
        typer.echo(f"reality_check_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
        typer.echo(f"known_gap_count={len(check.known_gaps)}")
