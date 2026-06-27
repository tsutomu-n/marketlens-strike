from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import typer

from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.tournament import (
    CryptoPerpTournamentReport,
    NON_ACTUAL_CASH_KNOWN_GAPS,
    TournamentEventResult,
    build_tournament_report,
)

PREVIEW_ROWS_SCHEMA_VERSION = "crypto_perp_tournament_rows_preview.v1"
PREVIEW_ROWS_NOT_ACTUAL_CASH_ERROR = (
    "PREVIEW_ROWS_NOT_ACTUAL_CASH: crypto-perp-tournament-report requires actual-cash "
    "TournamentEventResult rows. Do not feed outcome-before-cost preview rows into this report; "
    "use crypto-perp-tournament-rows-v2 for estimates."
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _reject_preview_rows_input(schema_version: str | None, known_gaps: list[str]) -> None:
    if schema_version == PREVIEW_ROWS_SCHEMA_VERSION:
        raise ValueError(PREVIEW_ROWS_NOT_ACTUAL_CASH_ERROR)
    if any(gap in NON_ACTUAL_CASH_KNOWN_GAPS for gap in known_gaps):
        raise ValueError(PREVIEW_ROWS_NOT_ACTUAL_CASH_ERROR)


def _reject_non_actual_cash_rows(rows: list[TournamentEventResult]) -> None:
    if any(row.cash_metric_basis != "actual_cash" for row in rows):
        raise ValueError(PREVIEW_ROWS_NOT_ACTUAL_CASH_ERROR)


def _read_tournament_rows(path: Path) -> tuple[list[TournamentEventResult], list[str], str | None]:
    text = path.read_text(encoding="utf-8")
    rows_payload: object
    known_gaps: list[str] = []
    schema_version: str | None = None
    try:
        rows_payload = json.loads(text)
    except json.JSONDecodeError:
        rows_payload = [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(rows_payload, dict):
        raw_schema_version = rows_payload.get("schema_version")
        if isinstance(raw_schema_version, str):
            schema_version = raw_schema_version
        raw_known_gaps = rows_payload.get("known_gaps")
        if isinstance(raw_known_gaps, list):
            known_gaps = [str(gap) for gap in raw_known_gaps if str(gap).strip()]
        rows_payload = rows_payload.get("rows")
    _reject_preview_rows_input(schema_version, known_gaps)
    if not isinstance(rows_payload, list):
        raise ValueError("rows input must be a JSON array, JSON object with rows, or JSONL")
    rows = [TournamentEventResult.model_validate(row) for row in rows_payload]
    _reject_non_actual_cash_rows(rows)
    return (rows, known_gaps, schema_version)


def _render_tournament_report_markdown(report: CryptoPerpTournamentReport) -> str:
    lines = [
        "# Crypto Perp Tournament Report",
        "",
        f"- report_id: `{report.report_id}`",
        f"- tournament_status: `{report.tournament_status}`",
        f"- primary_metric: `{report.primary_metric}`",
        f"- primary_metric_display_name: `{report.primary_metric_display_name}`",
        f"- cash_metric_basis: `{report.cash_metric_basis}`",
        f"- actual_cash: `{str(report.actual_cash).lower()}`",
        f"- event_count: `{report.event_count}`",
        f"- leader_action: `{report.leader_action or 'NONE'}`",
        "",
        "## Scores",
        "",
        f"| action | {report.primary_metric_display_name} | largest_loss_usd | event_count | near_miss_count | operator_time_minutes |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for score in report.scores:
        lines.append(
            "| "
            f"{score.action} | "
            f"{score.actual_cash_result_usd} | "
            f"{score.largest_loss_usd} | "
            f"{score.event_count} | "
            f"{score.near_miss_count} | "
            f"{score.operator_time_minutes} |"
        )
    if report.inconclusive_reasons:
        lines.extend(["", "## Inconclusive Reasons", ""])
        lines.extend(f"- `{reason}`" for reason in report.inconclusive_reasons)
    if report.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in report.known_gaps)
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- permits_live_order: `false`",
            "- exchange_write_used: `false`",
            "- automatic_trading: `false`",
        ]
    )
    return "\n".join(lines)


def register_crypto_perp_tournament_report_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-tournament-report")
    def crypto_perp_tournament_report_cmd(
        rows: Path = typer.Option(
            ...,
            "--rows",
            help="Tournament rows as JSON array, JSON object with rows, or JSONL.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/tournament"),
            "--out",
            help="Output directory for tournament report artifacts.",
        ),
        report_id: str = typer.Option("crypto-perp-tournament", "--report-id"),
        min_events: int = typer.Option(10, "--min-events", min=1),
        known_gap: list[str] | None = typer.Option(
            None,
            "--known-gap",
            help="Known evidence gap to carry into the report.",
        ),
    ) -> None:
        try:
            row_list, source_known_gaps, source_schema_version = _read_tournament_rows(rows)
            source_text = rows.read_text(encoding="utf-8")
            combined_known_gaps = list(dict.fromkeys([*source_known_gaps, *(known_gap or [])]))
            _reject_preview_rows_input(source_schema_version, combined_known_gaps)
            source_ref = {
                "path": rows.as_posix(),
                "sha256": "sha256:" + stable_hash([source_text]),
            }
            if source_schema_version:
                source_ref["schema_version"] = source_schema_version
            report = build_tournament_report(
                report_id=report_id,
                generated_at=_utc_now(),
                rows=row_list,
                min_events=min_events,
                source_refs=[source_ref],
                known_gaps=combined_known_gaps,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "tournament_report.json"
        report_path = out / "tournament_report.md"
        write_json_artifact(json_path, report.model_dump(mode="json"))
        write_text_artifact(report_path, _render_tournament_report_markdown(report))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo(
            "status=pass" if report.tournament_status == "COMPLETE" else "status=inconclusive"
        )
        typer.echo(f"tournament_status={report.tournament_status}")
        typer.echo(f"leader_action={report.leader_action or 'NONE'}")
        typer.echo(f"primary_metric={report.primary_metric}")
        typer.echo(f"primary_metric_display_name={report.primary_metric_display_name}")
        typer.echo(f"cash_metric_basis={report.cash_metric_basis}")
        typer.echo(f"actual_cash={str(report.actual_cash).lower()}")
        typer.echo(f"event_count={report.event_count}")
        typer.echo(f"tournament_report_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
