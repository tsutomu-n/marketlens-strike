from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

import typer

from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.tournament_rows import (
    CryptoPerpTournamentRowsPreview,
    build_tournament_rows_preview,
)


def _render_preview_markdown(preview: CryptoPerpTournamentRowsPreview) -> str:
    lines = [
        "# Crypto Perp Tournament Rows Preview",
        "",
        f"- event_id: `{preview.event_id}`",
        f"- outcome_id: `{preview.outcome_id}`",
        f"- primary_metric_source: `{preview.primary_metric_source}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Rows",
        "",
        "| action | outcome_before_cost_proxy_usd | market_adjusted_return |",
        "|---|---:|---:|",
    ]
    for row in preview.rows:
        lines.append(
            f"| {row.action} | {row.actual_cash_result_usd} | {row.market_adjusted_return} |"
        )
    if preview.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in preview.known_gaps)
    return "\n".join(lines)


def register_crypto_perp_tournament_rows_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-tournament-rows-preview")
    def crypto_perp_tournament_rows_preview_cmd(
        outcome: Path = typer.Option(
            ...,
            "--outcome",
            help="Source crypto_perp_outcome.v1 JSON artifact.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/tournament_rows_preview"),
            "--out",
            help="Output directory for tournament rows preview artifacts.",
        ),
        notional_usd: str = typer.Option(
            "0",
            "--notional-usd",
            help="Proxy notional for before-cost row preview. Use 0 when cash basis is unavailable.",
        ),
        operator_time_minutes: str = typer.Option("0", "--operator-time-minutes"),
    ) -> None:
        try:
            payload = json.loads(outcome.read_text(encoding="utf-8"))
            preview = build_tournament_rows_preview(
                outcome=CryptoPerpOutcome.model_validate(payload),
                notional_usd=Decimal(notional_usd),
                operator_time_minutes=Decimal(operator_time_minutes),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        rows_jsonl = "\n".join(
            json.dumps(row.model_dump(mode="json"), ensure_ascii=False) for row in preview.rows
        )
        write_json_artifact(out / "tournament_rows_preview.json", preview.model_dump(mode="json"))
        write_text_artifact(out / "tournament_rows.jsonl", rows_jsonl)
        write_text_artifact(out / "tournament_rows_preview.md", _render_preview_markdown(preview))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("status=pass")
        typer.echo(f"event_id={preview.event_id}")
        typer.echo(f"known_gap_count={len(preview.known_gaps)}")
        typer.echo(f"rows_path={(out / 'tournament_rows.jsonl').as_posix()}")
        typer.echo(f"preview_path={(out / 'tournament_rows_preview.json').as_posix()}")
