from __future__ import annotations

from pathlib import Path

import typer

from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.truth_cycle_status import (
    CryptoPerpTruthCycleStatus,
    build_truth_cycle_status,
)


def _render_truth_cycle_status_markdown(status: CryptoPerpTruthCycleStatus) -> str:
    lines = [
        "# Crypto Perp Truth-Cycle Status",
        "",
        f"- cycle_status: `{status.cycle_status}`",
        f"- recommended_next_command: `{status.recommended_next_command}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "- live_order_submitted: `false`",
        "",
        "## Stages",
        "",
    ]
    lines.extend(
        f"- `{stage.stage_id}`: `{stage.status}`"
        + (f" ({stage.artifact_path})" if stage.artifact_path else "")
        for stage in status.stages
    )
    if status.stop_reasons:
        lines.extend(["", "## Stop Reasons", ""])
        lines.extend(f"- `{reason}`" for reason in status.stop_reasons)
    if status.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in status.known_gaps)
    return "\n".join(lines)


def register_crypto_perp_truth_cycle_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-truth-cycle-status")
    def crypto_perp_truth_cycle_status_cmd(
        probe_audit: Path | None = typer.Option(
            None,
            "--probe-audit",
            help="Optional crypto_perp_probe_audit.v1 JSON artifact.",
        ),
        raw_refresh: Path | None = typer.Option(
            None,
            "--raw-refresh",
            help="Optional crypto_perp_raw_refresh.v1 JSON artifact.",
        ),
        event: Path | None = typer.Option(
            None,
            "--event",
            help="Optional crypto_perp_event.v1 JSON artifact.",
        ),
        decision: Path | None = typer.Option(
            None,
            "--decision",
            help="Optional crypto_perp_decision.v1 JSON artifact.",
        ),
        outcome: Path | None = typer.Option(
            None,
            "--outcome",
            help="Optional crypto_perp_outcome.v1 JSON artifact.",
        ),
        rows_preview: Path | None = typer.Option(
            None,
            "--rows-preview",
            help="Optional crypto_perp_tournament_rows_preview.v1 JSON artifact.",
        ),
        tournament_report: Path | None = typer.Option(
            None,
            "--tournament-report",
            help="Optional crypto_perp_tournament_report.v1 JSON artifact.",
        ),
        tournament_gate: Path | None = typer.Option(
            None,
            "--tournament-gate",
            help="Optional crypto_perp_tournament_gate.v1 JSON artifact.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/truth_cycle_status"),
            "--out",
            help="Output directory for truth-cycle status artifacts.",
        ),
    ) -> None:
        try:
            status = build_truth_cycle_status(
                probe_audit_path=probe_audit,
                raw_refresh_path=raw_refresh,
                event_path=event,
                decision_path=decision,
                outcome_path=outcome,
                rows_preview_path=rows_preview,
                tournament_report_path=tournament_report,
                tournament_gate_path=tournament_gate,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "truth_cycle_status.json"
        report_path = out / "truth_cycle_status.md"
        write_json_artifact(json_path, status.model_dump(mode="json"))
        write_text_artifact(report_path, _render_truth_cycle_status_markdown(status))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"cycle_status={status.cycle_status}")
        typer.echo(f"recommended_next_command={status.recommended_next_command}")
        typer.echo(f"known_gap_count={len(status.known_gaps)}")
        typer.echo(f"status_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
