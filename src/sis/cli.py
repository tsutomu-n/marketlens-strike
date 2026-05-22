from __future__ import annotations

from datetime import datetime, timezone

import typer
from loguru import logger

from sis.reports.cost_matrix import build_initial_cost_matrix
from sis.reports.evidence import build_evidence_card
from sis.reports.go_no_go import build_go_no_go_report, write_go_no_go_markdown
from sis.risk.halt_policy import load_halt_policy, summarize_halt_policy
from sis.risk.scalping_policy import check_timeframe
from sis.settings import get_settings
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import normalize_quotes
from sis.venues.gtrade.quotes import convert_sidecar_to_quote_logs, latest_sidecar_file
from sis.venues.gtrade.registry import GTRADE_TARGETS
from sis.venues.ostium.registry import OSTIUM_TARGETS

app = typer.Typer(no_args_is_help=True)
probe_app = typer.Typer(no_args_is_help=True)
app.add_typer(probe_app, name="probe")


@probe_app.command("gtrade")
def probe_gtrade() -> None:
    settings = get_settings()
    out = settings.data_dir / "registry/gtrade_instrument_registry.json"
    write_json(out, [item.model_dump(mode="json") for item in GTRADE_TARGETS])
    logger.info("written: {}", out)


@probe_app.command("ostium")
def probe_ostium() -> None:
    settings = get_settings()
    out = settings.data_dir / "registry/ostium_instrument_registry.json"
    write_json(out, [item.model_dump(mode="json") for item in OSTIUM_TARGETS])
    logger.info("written: {}", out)
    typer.echo("Ostium registry written with requires_probe fields; no live SDK call was made.")


@app.command("log-quotes")
def log_quotes(venue: str = typer.Option(..., "--venue")) -> None:
    settings = get_settings()
    normalized_venue = venue.strip().lower()
    if normalized_venue != "gtrade":
        typer.echo("Only gtrade sidecar ingestion is available in the initial scaffold.")
        raise typer.Exit(code=2)

    try:
        sidecar = latest_sidecar_file(settings.data_dir / "raw/sidecar/gtrade")
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
    day = datetime.now(timezone.utc).date().isoformat()
    out = settings.data_dir / f"raw/quotes/gtrade/{day}.jsonl"
    count = convert_sidecar_to_quote_logs(sidecar, out)
    logger.info("written {} quote rows: {}", count, out)


@app.command("normalize-quotes")
def normalize_quotes_cmd() -> None:
    settings = get_settings()
    try:
        count = normalize_quotes(
            settings.data_dir / "raw/quotes",
            settings.data_dir / "normalized/quotes.parquet",
            settings.data_dir / "normalized/sis.duckdb",
        )
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
    logger.info("normalized {} quote rows", count)


@app.command("build-cost-matrix")
def build_cost_matrix() -> None:
    settings = get_settings()
    out = settings.data_dir / "research/venue_cost_matrix.csv"
    build_initial_cost_matrix(out)
    logger.info("written: {}", out)


@app.command("check-halt-policy")
def check_halt_policy() -> None:
    policy = load_halt_policy()
    for line in summarize_halt_policy(policy):
        typer.echo(line)


@app.command("check-go-no-go")
def check_go_no_go() -> None:
    settings = get_settings()
    report = build_go_no_go_report(settings.data_dir)
    out = settings.data_dir / "research/go_no_go_report.md"
    write_go_no_go_markdown(report, out)
    logger.info("written: {}", out)
    typer.echo(report.decision.value)


@app.command("build-evidence-card")
def build_evidence_card_cmd() -> None:
    settings = get_settings()
    out = build_evidence_card(settings.data_dir, settings.data_dir / "evidence")
    logger.info("written: {}", out)


@app.command("check-timeframe")
def check_timeframe_cmd(timeframe: str) -> None:
    decision = check_timeframe(timeframe)
    if decision.allowed:
        typer.echo(f"ALLOW: {timeframe}")
        return
    typer.echo(f"BLOCK: {timeframe} reason={decision.reason}")
    raise typer.Exit(code=2)


def main() -> None:
    app()
