from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

import typer

from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.tournament import CryptoPerpTournamentReport
from sis.crypto_perp.tournament_gate import (
    CryptoPerpTournamentGate,
    TournamentGatePolicy,
    build_tournament_gate,
)


def _render_gate_markdown(gate: CryptoPerpTournamentGate) -> str:
    lines = [
        "# Crypto Perp Tournament Gate",
        "",
        f"- gate_id: `{gate.gate_id}`",
        f"- report_id: `{gate.report_id}`",
        f"- gate_status: `{gate.gate_status}`",
        f"- recommended_action: `{gate.recommended_action}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Failed Conditions",
        "",
    ]
    if gate.failed_conditions:
        lines.extend(
            f"- `{condition.condition_id}` observed `{condition.observed}` required `{condition.required}`"
            for condition in gate.failed_conditions
        )
    else:
        lines.append("- none")
    if gate.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in gate.known_gaps)
    return "\n".join(lines)


def register_crypto_perp_tournament_gate_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-tournament-gate")
    def crypto_perp_tournament_gate_cmd(
        report: Path = typer.Option(
            ...,
            "--report",
            help="Source crypto_perp_tournament_report.v1 JSON artifact.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/tournament_gate"),
            "--out",
            help="Output directory for tournament gate artifacts.",
        ),
        gate_id: str | None = typer.Option(None, "--gate-id"),
        max_largest_loss_usd: str = typer.Option("25", "--max-largest-loss-usd"),
        max_profit_concentration: str = typer.Option("0.60", "--max-profit-concentration"),
        max_operator_time_minutes: str = typer.Option("120", "--max-operator-time-minutes"),
        allow_no_trade_leader: bool = typer.Option(False, "--allow-no-trade-leader"),
    ) -> None:
        try:
            source_text = report.read_text(encoding="utf-8")
            tournament_report = CryptoPerpTournamentReport.model_validate(json.loads(source_text))
            gate = build_tournament_gate(
                report=tournament_report,
                created_at=tournament_report.generated_at,
                gate_id=gate_id,
                policy=TournamentGatePolicy(
                    max_largest_loss_usd=Decimal(max_largest_loss_usd),
                    max_profit_concentration=Decimal(max_profit_concentration),
                    max_operator_time_minutes=Decimal(max_operator_time_minutes),
                    allow_no_trade_leader=allow_no_trade_leader,
                ),
                source_refs=[
                    {
                        "path": report.as_posix(),
                        "sha256": "sha256:" + stable_hash([source_text]),
                        "schema_version": tournament_report.schema_version,
                    }
                ],
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "tournament_gate.json"
        report_path = out / "tournament_gate.md"
        write_json_artifact(json_path, gate.model_dump(mode="json"))
        write_text_artifact(report_path, _render_gate_markdown(gate))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo(
            "status=pass"
            if gate.gate_status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
            else "status=blocked"
        )
        typer.echo(f"gate_status={gate.gate_status}")
        typer.echo(f"recommended_action={gate.recommended_action}")
        typer.echo(f"failed_condition_count={len(gate.failed_conditions)}")
        typer.echo(f"gate_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
