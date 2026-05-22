from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer
from loguru import logger

from sis.backtest.bridge import (
    run_backtest_bridge,
    write_backtest_metrics_json,
    write_backtest_report,
)
from sis.market_calendar import market_session_window
from sis.reports.cost_matrix import build_cost_matrix_from_quotes
from sis.reports.evidence import build_evidence_card
from sis.reports.go_no_go import build_go_no_go_report, write_go_no_go_markdown
from sis.reports.implementation_status import implementation_status_items, write_implementation_status
from sis.reports.quote_diagnostics import build_quote_diagnostics
from sis.risk.halt_policy import load_halt_policy, summarize_halt_policy
from sis.risk.scalping_policy import check_timeframe
from sis.settings import get_settings
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import normalize_quotes
from sis.validation.artifacts import validate_artifacts
from sis.venues.gtrade.quotes import convert_sidecar_to_quote_logs, latest_pricing_file, latest_sidecar_file
from sis.venues.gtrade.registry import GTRADE_TARGETS
from sis.venues.ostium.probe import OSTIUM_PRICES_ENDPOINT, write_ostium_live_probe_outputs
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
def probe_ostium(
    read_only_live: bool = typer.Option(
        False,
        "--read-only-live",
        help="Fetch Ostium Builder API prices with a GET-only probe before writing the registry.",
    ),
    endpoint: str = typer.Option(OSTIUM_PRICES_ENDPOINT, "--endpoint", help="Ostium prices endpoint."),
    pairs_metadata_path: Path | None = typer.Option(
        None,
        "--pairs-metadata-path",
        help="Optional Ostium SDK getPairs sidecar JSON path.",
    ),
) -> None:
    settings = get_settings()
    out = settings.data_dir / "registry/ostium_instrument_registry.json"
    if read_only_live:
        targets, quotes = write_ostium_live_probe_outputs(
            data_dir=settings.data_dir,
            endpoint=endpoint,
            pairs_metadata_path=pairs_metadata_path,
        )
    else:
        targets = OSTIUM_TARGETS
        quotes = []
    write_json(out, [item.model_dump(mode="json") for item in targets])
    logger.info("written: {}", out)
    if read_only_live:
        typer.echo(f"Ostium registry and {len(quotes)} quote rows written from read-only probe.")
    else:
        typer.echo("Ostium registry written with requires_probe fields; pass --read-only-live to probe.")


@app.command("log-quotes")
def log_quotes(
    venue: str = typer.Option(..., "--venue"),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Replace the generated daily quote JSONL before replaying the sidecar.",
    ),
) -> None:
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
    if replace and out.exists():
        out.unlink()
    pricing = None
    pricing_root = settings.data_dir / "raw/sidecar/gtrade-pricing"
    if pricing_root.exists():
        try:
            pricing = latest_pricing_file(pricing_root)
        except FileNotFoundError:
            pricing = None
    count = convert_sidecar_to_quote_logs(sidecar, out, pricing_path=pricing)
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
    build_cost_matrix_from_quotes(
        settings.data_dir / "normalized/quotes.parquet",
        out,
        gtrade_sidecar_root=settings.data_dir / "raw/sidecar/gtrade",
        ostium_registry_path=settings.data_dir / "registry/ostium_instrument_registry.json",
    )
    logger.info("written: {}", out)


@app.command("build-backtest")
def build_backtest(
    signals_path: Path | None = typer.Option(
        None,
        "--signals-path",
        help="Optional research signal CSV. Defaults to data/research/signals.csv when present.",
    )
) -> None:
    settings = get_settings()
    default_signals_path = settings.data_dir / "research/signals.csv"
    selected_signals_path = signals_path or default_signals_path
    if signals_path is not None and not selected_signals_path.exists():
        typer.echo(f"Research signal CSV not found: {selected_signals_path}")
        raise typer.Exit(code=2)
    metrics = run_backtest_bridge(
        settings.data_dir / "normalized/quotes.parquet",
        selected_signals_path if selected_signals_path.exists() else None,
        settings.data_dir / "research/venue_cost_matrix.csv",
    )
    report_path = settings.data_dir / "research/backtest_report.md"
    metrics_path = settings.data_dir / "research/backtest_metrics.json"
    write_backtest_report(
        metrics,
        report_path,
        selected_signals_path if selected_signals_path.exists() else None,
    )
    write_backtest_metrics_json(metrics, metrics_path)
    logger.info("written: {}", report_path)
    logger.info("written: {}", metrics_path)


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


@app.command("implementation-status")
def implementation_status(write: bool = typer.Option(False, "--write")) -> None:
    if write:
        out = Path("docs/IMPLEMENTATION_STATUS.md")
        write_implementation_status(out)
        logger.info("written: {}", out)
    for item in implementation_status_items():
        typer.echo(f"{item.status}\t{item.area}\t{item.item}")


@app.command("check-timeframe")
def check_timeframe_cmd(timeframe: str) -> None:
    decision = check_timeframe(timeframe)
    if decision.allowed:
        typer.echo(f"ALLOW: {timeframe}")
        return
    typer.echo(f"BLOCK: {timeframe} reason={decision.reason}")
    raise typer.Exit(code=2)


@app.command("market-session")
def market_session(venue: str = typer.Option(..., "--venue"), symbol: str = typer.Option(..., "--symbol")) -> None:
    try:
        window = market_session_window(venue, symbol)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
    typer.echo(f"symbol={window.symbol}")
    typer.echo(f"venue={window.venue}")
    typer.echo(f"calendar={window.calendar}")
    typer.echo(f"now_jst={window.now_jst.isoformat()}")
    typer.echo(f"market_status={window.market_status}")
    typer.echo(f"next_open_jst={window.next_open_jst.isoformat()}")
    typer.echo(f"next_close_jst={window.next_close_jst.isoformat()}")


@app.command("next-live-window")
def next_live_window(venue: str = typer.Option(..., "--venue"), symbol: str = typer.Option(..., "--symbol")) -> None:
    try:
        window = market_session_window(venue, symbol)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
    typer.echo(f"symbol={window.symbol}")
    typer.echo(f"venue={window.venue}")
    typer.echo(f"calendar={window.calendar}")
    typer.echo(f"now_jst={window.now_jst.isoformat()}")
    typer.echo(f"market_status={window.market_status}")
    typer.echo(f"next_open_jst={window.next_open_jst.isoformat()}")
    typer.echo(f"next_close_jst={window.next_close_jst.isoformat()}")
    typer.echo(f"recommended_start_jst={window.recommended_start_jst.isoformat()}")
    typer.echo(f"recommended_end_jst={window.recommended_end_jst.isoformat()}")


@app.command("validate-artifacts")
def validate_artifacts_cmd(strict: bool = typer.Option(False, "--strict")) -> None:
    settings = get_settings()
    summary = validate_artifacts(settings.data_dir, Path("schemas"), strict=strict)
    typer.echo(f"checked_files={summary.checked_files}")
    typer.echo(f"issues={len(summary.issues)}")
    for issue in summary.issues:
        typer.echo(f"{issue.path}: {issue.message}")
    if summary.issues:
        raise typer.Exit(code=2)


@app.command("diagnose-quotes")
def diagnose_quotes(
    venue: str | None = typer.Option(None, "--venue"),
    symbol: str | None = typer.Option(None, "--symbol"),
) -> None:
    settings = get_settings()
    diagnostics = build_quote_diagnostics(settings.data_dir / "raw/quotes", venue=venue, symbol=symbol)
    if not diagnostics:
        typer.echo("No quote rows found for diagnostics.")
        raise typer.Exit(code=2)
    for item in diagnostics:
        typer.echo(f"venue={item.venue} symbol={item.symbol}")
        typer.echo(f"rows={item.rows}")
        typer.echo(f"market_open_rows={item.market_open_rows}")
        typer.echo(f"tradable_rate={item.tradable_rate:.4f}")
        typer.echo(f"stale_rate={item.stale_rate:.4f}")
        typer.echo(f"missing_mark_price_rate={item.missing_mark_price_rate:.4f}")
        typer.echo(f"missing_index_price_rate={item.missing_index_price_rate:.4f}")
        typer.echo(f"missing_spread_rate={item.missing_spread_rate:.4f}")
        typer.echo(f"stale_missing_oracle_ts_rate={item.stale_missing_oracle_ts_rate:.4f}")
        typer.echo(f"stale_old_oracle_ts_rate={item.stale_old_oracle_ts_rate:.4f}")
        typer.echo(f"market_status_unknown_rate={item.market_status_unknown_rate:.4f}")
        typer.echo(f"market_closed_rate={item.market_closed_rate:.4f}")
        typer.echo(f"oracle_age_p50_ms={item.oracle_age_p50_ms}")
        typer.echo(f"oracle_age_p90_ms={item.oracle_age_p90_ms}")
        typer.echo(f"spread_p50_bps={item.spread_p50_bps}")
        typer.echo(f"spread_p90_bps={item.spread_p90_bps}")


def main() -> None:
    app()
