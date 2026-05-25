from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import polars as pl
import typer
from loguru import logger

from sis.backtest.bridge import (
    run_backtest_bridge_with_decisions,
    write_backtest_metrics_json,
    write_backtest_metrics_summary_json,
    write_backtest_report,
)
from sis.execution.base import OrderIntent
from sis.execution.gtrade_adapter import GTradeExecutionAdapter
from sis.execution.ostium_adapter import OstiumExecutionAdapter
from sis.market_calendar import market_session_window
from sis.ops.daily_loss_limit import evaluate_daily_loss_limit, evaluate_max_exposure
from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.ops.alerts import write_alert
from sis.ops.daemon import create_daemon_manifest, run_daemon_dry_run, write_daemon_manifest
from sis.ops.manifest_chain import append_operation_manifest, create_operation_manifest, latest_operation_manifest
from sis.ops.scheduler import next_interval_run, schedule_run, write_schedule_with_audit
from sis.ops.monitoring import build_monitoring_snapshot, write_monitoring_snapshot
from sis.paper.fills import PaperFill
from sis.paper.portfolio import PaperPosition
from sis.paper.report import build_daily_paper_report
from sis.paper.runner import run_paper_step
from sis.research.event_calendar import build_event_calendar
from sis.research.feature_panel import build_feature_panel
from sis.research.macro_ingest import build_macro_panel
from sis.research.price_ingest import build_market_panel
from sis.research.providers import FredMacroProvider
from sis.research.research_quality import build_research_quality_report
from sis.research.signal_builder import build_signals
from sis.reports.cost_matrix import build_cost_matrix_from_quotes
from sis.reports.cost_matrix import build_cost_matrix_report
from sis.reports.audit_bundle_history import build_audit_bundle_history_report
from sis.reports.audit_bundle import build_audit_bundle_manifest
from sis.reports.comparison import build_paper_live_comparison_report
from sis.reports.current_state_index import build_current_state_index
from sis.reports.execution_drift_overview import build_execution_drift_overview_report
from sis.reports.execution_adapter_status import (
    build_action_status_report,
    build_balance_status_report,
    build_fill_status_report,
    build_order_status_report,
    build_execution_read_only_surfaces_report,
    build_reconcile_positions_report,
)
from sis.reports.execution_gap_history import build_execution_gap_history_report
from sis.reports.execution_snapshot_drift_history import build_execution_snapshot_drift_history_report
from sis.reports.execution_state_comparison_history import build_execution_state_comparison_history_report
from sis.reports.execution_venue_comparison import build_execution_venue_comparison_report
from sis.reports.execution_venue_diagnostics import build_execution_venue_diagnostics_report
from sis.reports.execution_snapshot import build_execution_snapshot_report
from sis.reports.audit_dashboard import build_audit_dashboard
from sis.reports.evidence import build_evidence_card
from sis.reports.go_no_go import build_go_no_go_report, write_go_no_go_markdown
from sis.reports.implementation_status import implementation_status_items, write_implementation_status
from sis.reports.lifecycle import build_strategy_lifecycle_report
from sis.reports.audit_timeline import build_audit_timeline_report
from sis.reports.operations_audit_pack import build_operations_audit_pack
from sis.reports.operations_bundle import build_operations_bundle_manifest
from sis.reports.ops_review import build_ops_review_report
from sis.reports.operations_timeline import build_operations_timeline_report
from sis.reports.paper_cycle_history import build_paper_cycle_history_report
from sis.reports.phase_gate_review import build_phase_gate_review
from sis.reports.readiness_snapshot import build_readiness_snapshot
from sis.reports.remediation_execution_plan import build_remediation_execution_plan
from sis.reports.remediation_planner import build_remediation_planner
from sis.reports.remediation_session import build_remediation_session
from sis.reports.remediation_session_checkpoint import build_remediation_session_checkpoint
from sis.reports.remediation_scoreboard import build_remediation_scoreboard
from sis.reports.remediation_evaluator import build_remediation_evaluator
from sis.reports.remediation_evidence import build_remediation_evidence
from sis.reports.remediation_command_results import build_remediation_command_results
from sis.reports.state_command_status import (
    build_daemon_manifest_report,
    build_state_export_report,
    build_state_restore_report,
)
from sis.reports.operations_dashboard import build_operations_dashboard
from sis.reports.ops_command_status import (
    build_alert_report,
    build_healthcheck_report,
    build_kill_switch_report,
    build_schedule_run_report,
)
from sis.reports.paper_operations_runbook import build_paper_operations_runbook
from sis.reports.quote_diagnostics import build_quote_diagnostics
from sis.reports.quote_diagnostics import build_quote_diagnostics_report
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    normalize_execution_gap_history_summary,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_snapshot_summary,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    defaulted_all_latest_execution_lineage_fields,
    latest_execution_lineage_payload_from_summary,
    phase_gate_flat_fields,
    phase_gate_issue_note_lines,
    phase_gate_nested_fields,
    readiness_flat_fields,
)
from sis.reports.weekly_review import build_weekly_review_report
from sis.risk.halt_policy import load_halt_policy, summarize_halt_policy
from sis.risk.scalping_policy import check_timeframe
from sis.settings import get_settings
from sis.state.reconciliation import reconcile_positions
from sis.state.recovery import export_state_snapshot, restore_state_snapshot
from sis.state.store import StateStore
from sis.storage.jsonl_store import read_json, write_json
from sis.storage.normalize import normalize_quotes
from sis.validation.artifacts import validate_artifacts
from sis.venues.gtrade.quotes import convert_sidecar_to_quote_logs, latest_pricing_file, latest_sidecar_file
from sis.venues.gtrade.registry import GTRADE_TARGETS
from sis.venues.ostium.probe import OSTIUM_PRICES_ENDPOINT, write_ostium_live_probe_outputs
from sis.venues.ostium.positions import latest_positions_sidecar
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
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


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
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


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
    build_cost_matrix_report(
        cost_matrix_path=out,
        out_path=settings.data_dir / "reports/venue_cost_matrix.md",
        summary_path=settings.data_dir / "ops/venue_cost_matrix_summary.json",
    )
    logger.info("written: {}", out)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("ingest-research-data")
def ingest_research_data() -> None:
    settings = get_settings()
    market_panel = build_market_panel(settings.data_dir)
    macro_panel = build_macro_panel(
        settings.data_dir,
        provider=FredMacroProvider(api_key=settings.fred_api_key),
    )
    logger.info("written: {}", market_panel)
    logger.info("written: {}", macro_panel)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("build-event-calendar")
def build_event_calendar_cmd(
    csv_path: Path | None = typer.Option(
        None,
        "--csv-path",
        help="Optional event calendar CSV path. Defaults to data/research/event_calendar.csv.",
    )
) -> None:
    settings = get_settings()
    out = build_event_calendar(settings.data_dir, csv_path=csv_path)
    logger.info("written: {}", out)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("build-feature-panel")
def build_feature_panel_cmd() -> None:
    settings = get_settings()
    out = build_feature_panel(settings.data_dir)
    logger.info("written: {}", out)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("build-signals")
def build_signals_cmd() -> None:
    settings = get_settings()
    out = build_signals(settings.data_dir)
    logger.info("written: {}", out)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("check-research-quality")
def check_research_quality_cmd() -> None:
    settings = get_settings()
    out = build_research_quality_report(settings.data_dir)
    logger.info("written: {}", out)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


def _state_store(settings_data_dir: Path, state_path: Path | None) -> StateStore:
    return StateStore(state_path or (settings_data_dir / "state/marketlens.sqlite"))


def _adapter_for_venue(settings_data_dir: Path, venue: str):
    normalized = venue.strip().lower()
    if normalized == "gtrade":
        return GTradeExecutionAdapter(
            registry_path=settings_data_dir / "registry/gtrade_instrument_registry.json",
            balance_snapshot_path=settings_data_dir / "execution/gtrade_balance.json",
            positions_snapshot_path=settings_data_dir / "paper/positions.parquet",
            fills_snapshot_path=settings_data_dir / "execution/gtrade_fills.json",
            order_status_path=settings_data_dir / "execution/gtrade_order_status.json",
        )
    if normalized == "ostium":
        return OstiumExecutionAdapter(
            registry_path=settings_data_dir / "registry/ostium_instrument_registry.json",
            positions_root=settings_data_dir / "raw/sidecar/ostium",
            balance_snapshot_path=settings_data_dir / "execution/ostium_balance.json",
            fills_snapshot_path=settings_data_dir / "execution/ostium_fills.json",
            order_status_path=settings_data_dir / "execution/ostium_order_status.json",
        )
    raise typer.BadParameter(f"Unsupported venue: {venue}")


def _execution_snapshot_for_venue(
    settings_data_dir: Path,
    venue: str,
    *,
    fills_limit: int,
    order_limit: int,
) -> dict:
    adapter = _adapter_for_venue(settings_data_dir, venue)
    balance = adapter.read_balance()
    positions = adapter.read_positions()
    fills = adapter.read_fills(limit=fills_limit)
    order_statuses = adapter.read_order_statuses(limit=order_limit)
    health = adapter.healthcheck()
    return {
        "venue": venue.strip().lower(),
        "registry_exists": health.get("registry_exists"),
        "balance_snapshot_exists": health.get("balance_snapshot_exists"),
        "positions_snapshot_exists": health.get("positions_snapshot_exists"),
        "fills_snapshot_exists": health.get("fills_snapshot_exists"),
        "order_status_snapshot_exists": health.get("order_status_snapshot_exists"),
        "positions_count": len(positions),
        "fills_count": len(fills),
        "order_status_count": len(order_statuses),
        "balance": balance,
        "latest_fill": fills[0].__dict__ if fills else None,
        "latest_order_status": order_statuses[0].__dict__ if order_statuses else None,
    }


def _write_execution_snapshot(
    settings_data_dir: Path,
    *,
    venue: str | None = None,
    fills_limit: int = 5,
    order_limit: int = 5,
) -> tuple[Path, Path, str]:
    venues = [venue] if venue is not None else ["gtrade", "ostium"]
    venue_snapshots = [
        _execution_snapshot_for_venue(
            settings_data_dir,
            venue_name,
            fills_limit=fills_limit,
            order_limit=order_limit,
        )
        for venue_name in venues
    ]
    out = settings_data_dir / "reports/execution_snapshot.md"
    summary_out = settings_data_dir / "ops/execution_snapshot_summary.json"
    text = build_execution_snapshot_report(
        venue_snapshots=venue_snapshots,
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_venue_comparison(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_venue_comparison.md"
    summary_out = settings_data_dir / "ops/execution_venue_comparison_summary.json"
    text = build_execution_venue_comparison_report(
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_venue_diagnostics(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_venue_diagnostics.md"
    summary_out = settings_data_dir / "ops/execution_venue_diagnostics_summary.json"
    text = build_execution_venue_diagnostics_report(
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_weekly_review(settings_data_dir: Path) -> tuple[Path, str]:
    out = settings_data_dir / "reports/weekly_strategy_review.md"
    text = build_weekly_review_report(
        backtest_metrics_path=settings_data_dir / "research/backtest_metrics.json",
        daily_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        paper_last_run_path=_paper_last_run_path(settings_data_dir),
        out_path=out,
    )
    return out, text


def _write_daemon_manifest_artifacts(settings_data_dir: Path) -> tuple[Path, Path, str] | None:
    manifest_path = settings_data_dir / "ops/daemon_manifest.json"
    if not manifest_path.exists():
        return None
    payload = read_json(manifest_path)
    if not isinstance(payload, dict):
        return None
    out = settings_data_dir / "reports/daemon_manifest.md"
    summary_out = settings_data_dir / "ops/daemon_manifest_summary.json"
    text = build_daemon_manifest_report(
        manifest=payload,
        manifest_path=str(manifest_path),
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_state_export_artifacts(
    settings_data_dir: Path,
    *,
    state_store_path: Path | None = None,
) -> tuple[Path, Path, str] | None:
    snapshot_path = settings_data_dir / "state/state_snapshot.json"
    if not snapshot_path.exists():
        return None
    payload = read_json(snapshot_path)
    if not isinstance(payload, dict):
        return None
    out = settings_data_dir / "reports/state_export.md"
    summary_out = settings_data_dir / "ops/state_export_summary.json"
    text = build_state_export_report(
        snapshot=payload,
        snapshot_path=str(snapshot_path),
        state_store_path=str(state_store_path or (settings_data_dir / "state/marketlens.sqlite")),
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_state_restore_artifacts(
    settings_data_dir: Path,
    *,
    snapshot_path: Path,
    state_store_path: Path | None = None,
    restored: bool,
) -> tuple[Path, Path, str] | None:
    if not snapshot_path.exists():
        return None
    payload = read_json(snapshot_path)
    if not isinstance(payload, dict):
        return None
    out = settings_data_dir / "reports/state_restore.md"
    summary_out = settings_data_dir / "ops/state_restore_summary.json"
    text = build_state_restore_report(
        snapshot=payload,
        snapshot_path=str(snapshot_path),
        state_store_path=str(state_store_path or (settings_data_dir / "state/marketlens.sqlite")),
        restored=restored,
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _paper_last_run_path(settings_data_dir: Path) -> Path | None:
    paper_last_run_path = settings_data_dir / "state/paper_last_run.json"
    if not paper_last_run_path.exists():
        store = _state_store(settings_data_dir, None)
        paper_last_run = store.get_json("paper_last_run")
        if paper_last_run is not None:
            paper_last_run_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(paper_last_run_path, paper_last_run)
    return paper_last_run_path if paper_last_run_path.exists() else None


def _write_lifecycle_report(settings_data_dir: Path) -> tuple[Path, str]:
    out = settings_data_dir / "reports/strategy_lifecycle_report.md"
    text = build_strategy_lifecycle_report(
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        weekly_review_path=settings_data_dir / "reports/weekly_strategy_review.md",
        paper_last_run_path=_paper_last_run_path(settings_data_dir),
        out_path=out,
    )
    return out, text


def _write_comparison_report(settings_data_dir: Path) -> tuple[Path, str]:
    out = settings_data_dir / "reports/paper_vs_backtest_comparison.md"
    text = build_paper_live_comparison_report(
        paper_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        backtest_metrics_path=settings_data_dir / "research/backtest_metrics.json",
        paper_last_run_path=_paper_last_run_path(settings_data_dir),
        out_path=out,
    )
    return out, text


def _paper_last_run_audit_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "audit",
        _read_audit_schedule_summary,
    )


def _paper_last_run_phase_gate_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "phase_gate",
        _read_phase_gate_schedule_summary,
    )


def _paper_last_run_execution_drift_overview_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_drift_overview_summary",
        _read_execution_drift_overview_schedule_summary,
    )


def _paper_last_run_readiness_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "readiness_summary",
        _read_readiness_schedule_summary,
    )


def _paper_last_run_execution_gap_history_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_gap_history_summary",
        _read_execution_gap_history_schedule_summary,
    )


def _paper_last_run_execution_state_comparison_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_state_comparison_summary",
        _read_execution_state_comparison_schedule_summary,
    )


def _paper_last_run_execution_snapshot_drift_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_snapshot_drift_summary",
        _read_execution_snapshot_drift_schedule_summary,
    )


def _read_execution_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_snapshot_summary.json",
        normalizer=normalize_execution_snapshot_summary,
        report_path="reports/execution_snapshot.md",
    )


def _paper_last_run_payload(settings_data_dir: Path) -> dict:
    paper_last_run_path = _paper_last_run_path(settings_data_dir)
    if paper_last_run_path is not None:
        return _read_json_dict(paper_last_run_path)
    return {}


def _read_json_dict(path: Path) -> dict:
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _read_normalized_schedule_summary(
    settings_data_dir: Path,
    *,
    path: Path,
    normalizer: Callable[[dict], dict],
    report_path: str | None = None,
    default: dict | None = None,
) -> dict:
    if not path.exists():
        return dict(default or {})
    payload = _read_json_dict(path)
    if not payload:
        return dict(default or {})
    if report_path is not None:
        payload = {
            **payload,
            "report_path": str(settings_data_dir / report_path),
        }
    return normalizer(payload)


def _paper_last_run_summary(
    settings_data_dir: Path,
    key: str,
    fallback_reader: Callable[[Path], dict],
) -> dict:
    payload = _paper_last_run_payload(settings_data_dir)
    summary = payload.get(key) if isinstance(payload, dict) else None
    if isinstance(summary, dict):
        return summary
    return fallback_reader(settings_data_dir)


def _paper_last_run_latest_execution_payload(settings_data_dir: Path) -> dict:
    return latest_execution_lineage_payload_from_summary(
        _paper_last_run_payload(settings_data_dir)
    )


def _read_execution_comparison_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        normalizer=normalize_execution_comparison_summary,
        report_path="reports/execution_venue_comparison.md",
    )


def _read_execution_diagnostics_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        normalizer=normalize_execution_diagnostics_summary,
        report_path="reports/execution_venue_diagnostics.md",
    )


def _read_execution_gap_history_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_gap_history_summary.json",
        normalizer=normalize_execution_gap_history_summary,
        report_path="reports/execution_gap_history.md",
        default={"entry_count": 0, "latest_status": None, "latest_execution_diagnostics_status": None},
    )


def _read_execution_state_comparison_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_state_comparison_history_summary.json",
        normalizer=normalize_execution_state_comparison_summary,
        report_path="reports/execution_state_comparison_history.md",
        default={"entry_count": 0, "latest_status_match": None, "mismatching_count": 0},
    )


def _read_execution_snapshot_drift_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_snapshot_drift_history_summary.json",
        normalizer=normalize_execution_snapshot_drift_summary,
        report_path="reports/execution_snapshot_drift_history.md",
        default={"entry_count": 0, "latest_status_match": None, "mismatching_snapshot_count": 0},
    )


def _read_execution_drift_overview_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        normalizer=normalize_execution_drift_overview_summary,
        report_path="reports/execution_drift_overview.md",
        default={
            "overall_status": None,
            "diagnostics_alignment_match": None,
            "state_comparison_mismatching_count": None,
            "snapshot_drift_mismatching_snapshot_count": None,
        },
    )


def _read_readiness_schedule_summary(settings_data_dir: Path) -> dict:
    readiness_path = settings_data_dir / "ops/readiness_snapshot.json"
    if not readiness_path.exists():
        return {}
    payload = _read_json_dict(readiness_path)
    if not payload:
        return {}
    return normalize_readiness_summary(
        {
            "overall_status": payload.get("overall_status"),
            "next_phase_candidate": payload.get("next_phase_candidate"),
            "execution_ready": payload.get("execution_ready"),
            "readiness_next_phase_candidate": payload.get("readiness_next_phase_candidate"),
            "readiness_execution_ready": payload.get("readiness_execution_ready"),
            "phase2_entry_allowed": payload.get("phase2_entry_allowed"),
            "report_path": str(settings_data_dir / "reports/readiness_snapshot.md"),
        }
    )


def _write_monitoring_snapshot(settings_data_dir: Path, state_path: Path | None) -> tuple[Path, dict]:
    store = _state_store(settings_data_dir, state_path)
    kill_switch = KillSwitch(settings_data_dir / "state/kill_switch.flag")
    health = build_healthcheck(
        kill_switch=kill_switch,
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        reconciliation_store_present=store.latest_reconciliation() is not None,
    )
    snapshot = build_monitoring_snapshot(
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        weekly_review_path=settings_data_dir / "reports/weekly_strategy_review.md",
        daily_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        last_healthcheck=health,
    )
    out = write_monitoring_snapshot(settings_data_dir / "ops/monitoring_status.json", snapshot)
    return out, snapshot


def _read_audit_schedule_summary(settings_data_dir: Path) -> dict:
    audit_dashboard_path = settings_data_dir / "ops/audit_dashboard_summary.json"
    audit_bundle_path = settings_data_dir / "ops/audit_bundle_manifest.json"
    audit_dashboard = _read_json_dict(audit_dashboard_path) if audit_dashboard_path.exists() else {}
    audit_bundle = _read_json_dict(audit_bundle_path) if audit_bundle_path.exists() else {}
    return audit_summary_fields(audit_dashboard, audit_bundle)


def _read_phase_gate_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/phase_gate_review_summary.json",
        normalizer=normalize_phase_gate_summary,
    )


def _phase_gate_note_lines(phase_gate: dict) -> list[str]:
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    lines = [
        f"phase_gate_decision={phase_gate_fields.get('phase_gate_decision')}",
        f"phase2_entry_allowed={phase_gate_fields.get('phase2_entry_allowed')}",
        f"phase_gate_reason={phase_gate_fields.get('phase_gate_reason')}",
        f"phase_gate_strict_validation_passed={phase_gate_fields.get('phase_gate_strict_validation_passed')}",
        (
            "phase_gate_strict_validation_issue_count="
            f"{phase_gate_fields.get('phase_gate_strict_validation_issue_count')}"
        ),
        f"phase_gate_checked_files={phase_gate_fields.get('phase_gate_checked_files')}",
    ]
    lines.append(
        f"phase_gate_review_report_path={phase_gate_fields.get('phase_gate_review_report_path')}"
    )
    lines.extend(phase_gate_issue_note_lines(phase_gate_fields))
    return lines


def _echo_audit_summary(summary: dict) -> None:
    audit_summary = audit_summary_fields(summary, summary)
    typer.echo(f"audit_overall_status={audit_summary.get('overall_status')}")
    typer.echo(f"audit_latest_operation={audit_summary.get('latest_operation')}")
    typer.echo(
        "audit_bundle_history_snapshot_count="
        f"{audit_summary.get('bundle_history_snapshot_count')}"
    )


def _readiness_note_lines(readiness: dict) -> list[str]:
    readiness_fields = readiness_flat_fields(readiness)
    return [
        f"readiness_next_phase={readiness_fields.get('readiness_next_phase_candidate')}",
        f"readiness_execution_ready={readiness_fields.get('readiness_execution_ready')}",
    ]


def _execution_drift_note_lines(drift_overview: dict) -> list[str]:
    drift_fields = execution_drift_overview_flat_fields(drift_overview)
    return [
        f"execution_drift_overview_status={drift_fields.get('execution_drift_overview_status')}",
        (
            "execution_drift_overview_diagnostics_alignment_match="
            f"{drift_fields.get('execution_drift_overview_diagnostics_alignment_match')}"
        ),
        (
            "execution_drift_overview_state_comparison_mismatching_count="
            f"{drift_fields.get('execution_drift_overview_state_comparison_mismatching_count')}"
        ),
        (
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
            f"{drift_fields.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
        ),
    ]


def _execution_gap_history_note_lines(gap_history: dict) -> list[str]:
    gap_history_fields = execution_gap_history_flat_fields(gap_history)
    return [
        f"execution_gap_history_entry_count={gap_history_fields.get('execution_gap_history_entry_count')}",
        f"execution_gap_history_latest_status={gap_history_fields.get('execution_gap_history_latest_status')}",
        (
            "execution_gap_history_latest_diagnostics_status="
            f"{gap_history_fields.get('execution_gap_history_latest_diagnostics_status')}"
        ),
    ]


def _execution_diagnostics_note_lines(execution_diagnostics: dict) -> list[str]:
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    return [
        (
            "execution_diagnostics_status="
            f"{execution_diagnostics_fields.get('execution_diagnostics_status')}"
        )
    ]


def _execution_summary_note_lines(execution_summary: dict) -> list[str]:
    execution_fields = execution_snapshot_flat_fields(execution_summary)
    return [
        f"execution_overall_status={execution_fields.get('execution_overall_status')}",
        f"execution_venue_count={execution_fields.get('execution_venue_count')}",
    ]


def _execution_comparison_note_lines(execution_comparison: dict) -> list[str]:
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    return [
        (
            "execution_comparison_all_registries_present="
            f"{execution_comparison_fields.get('execution_comparison_all_registries_present')}"
        )
    ]


def _execution_state_comparison_note_lines(state_comparison: dict) -> list[str]:
    state_comparison_fields = execution_state_comparison_flat_fields(state_comparison)
    return [
        (
            "execution_state_comparison_entry_count="
            f"{state_comparison_fields.get('execution_state_comparison_entry_count')}"
        ),
        (
            "execution_state_comparison_latest_status_match="
            f"{state_comparison_fields.get('execution_state_comparison_latest_status_match')}"
        ),
        (
            "execution_state_comparison_mismatching_count="
            f"{state_comparison_fields.get('execution_state_comparison_mismatching_count')}"
        ),
    ]


def _execution_snapshot_drift_note_lines(snapshot_drift: dict) -> list[str]:
    snapshot_drift_fields = execution_snapshot_drift_flat_fields(snapshot_drift)
    return [
        (
            "execution_snapshot_drift_entry_count="
            f"{snapshot_drift_fields.get('execution_snapshot_drift_entry_count')}"
        ),
        (
            "execution_snapshot_drift_latest_status_match="
            f"{snapshot_drift_fields.get('execution_snapshot_drift_latest_status_match')}"
        ),
        (
            "execution_snapshot_drift_mismatching_snapshot_count="
            f"{snapshot_drift_fields.get('execution_snapshot_drift_mismatching_snapshot_count')}"
        ),
    ]


def _echo_phase_gate_summary(phase_gate: dict) -> None:
    for line in _phase_gate_note_lines(phase_gate):
        typer.echo(line)


def _recommended_read_order(settings_data_dir: Path) -> list[str]:
    bundle_manifest_path = settings_data_dir / "ops/operations_bundle_manifest.json"
    if bundle_manifest_path.exists():
        payload = read_json(bundle_manifest_path)
        if isinstance(payload, dict):
            order = payload.get("recommended_read_order")
            if isinstance(order, list):
                return [str(item) for item in order]
    dashboard_summary_path = settings_data_dir / "ops/operations_dashboard_summary.json"
    if dashboard_summary_path.exists():
        payload = read_json(dashboard_summary_path)
        if isinstance(payload, dict):
            order = payload.get("recommended_read_order")
            if isinstance(order, list):
                return [str(item) for item in order]
    return [
        "docs/ACCEPTANCE_AUDIT.md",
        "docs/IMPLEMENTATION_STATUS.md",
        "data/ops/execution_snapshot_summary.json",
        "data/ops/operations_dashboard_summary.json",
        "data/ops/audit_dashboard_summary.json",
        "data/ops/operations_bundle_manifest.json",
        "data/ops/audit_bundle_manifest.json",
    ]


def _write_ops_review(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/ops_review_report.md"
    summary_out = settings_data_dir / "ops/ops_review_summary.json"
    text = build_ops_review_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        monitoring_snapshot_path=settings_data_dir / "ops/monitoring_status.json",
        daemon_dry_run_path=settings_data_dir / "ops/daemon_dry_run.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_operations_dashboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_dashboard.md"
    summary_out = settings_data_dir / "ops/operations_dashboard_summary.json"
    text = build_operations_dashboard(
        monitoring_snapshot_path=settings_data_dir / "ops/monitoring_status.json",
        operations_timeline_summary_path=settings_data_dir / "ops/operations_timeline_summary.json",
        ops_review_summary_path=settings_data_dir / "ops/ops_review_summary.json",
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        execution_balance_status_summary_path=settings_data_dir / "ops/execution_balance_status_summary.json",
        execution_fill_status_summary_path=settings_data_dir / "ops/execution_fill_status_summary.json",
        execution_order_status_summary_path=settings_data_dir / "ops/execution_order_status_summary.json",
        execution_cancel_order_summary_path=settings_data_dir / "ops/execution_cancel_order_summary.json",
        execution_close_position_summary_path=settings_data_dir / "ops/execution_close_position_summary.json",
        execution_reconcile_positions_summary_path=settings_data_dir / "ops/execution_reconcile_positions_summary.json",
        execution_read_only_surfaces_summary_path=settings_data_dir / "ops/execution_read_only_surfaces_summary.json",
        daemon_manifest_summary_path=settings_data_dir / "ops/daemon_manifest_summary.json",
        state_export_summary_path=settings_data_dir / "ops/state_export_summary.json",
        state_restore_summary_path=settings_data_dir / "ops/state_restore_summary.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        comparison_report_path=settings_data_dir / "reports/paper_vs_backtest_comparison.md",
        weekly_review_path=settings_data_dir / "reports/weekly_strategy_review.md",
        lifecycle_report_path=settings_data_dir / "reports/strategy_lifecycle_report.md",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_paper_operations_runbook(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/paper_operations_runbook.md"
    summary_out = settings_data_dir / "ops/paper_operations_runbook_summary.json"
    text = build_paper_operations_runbook(
        scheduled_run_path=settings_data_dir / "ops/scheduled_run.json",
        daemon_manifest_path=settings_data_dir / "ops/daemon_manifest.json",
        monitoring_snapshot_path=settings_data_dir / "ops/monitoring_status.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        ops_dashboard_summary_path=settings_data_dir / "ops/operations_dashboard_summary.json",
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        remediation_evaluator_summary_path=settings_data_dir / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_paper_cycle_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/paper_cycle_history_report.md"
    summary_out = settings_data_dir / "ops/paper_cycle_history_summary.json"
    text = build_paper_cycle_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_gap_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_gap_history.md"
    summary_out = settings_data_dir / "ops/execution_gap_history_summary.json"
    text = build_execution_gap_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_state_comparison_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_state_comparison_history.md"
    summary_out = settings_data_dir / "ops/execution_state_comparison_history_summary.json"
    text = build_execution_state_comparison_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_snapshot_drift_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_snapshot_drift_history.md"
    summary_out = settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
    text = build_execution_snapshot_drift_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_drift_overview(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_drift_overview.md"
    summary_out = settings_data_dir / "ops/execution_drift_overview_summary.json"
    text = build_execution_drift_overview_report(
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _has_target_free_execution_observation_sources(settings_data_dir: Path) -> bool:
    source_paths = [
        settings_data_dir / "execution/gtrade_balance.json",
        settings_data_dir / "execution/ostium_balance.json",
        settings_data_dir / "execution/gtrade_fills.json",
        settings_data_dir / "execution/ostium_fills.json",
        settings_data_dir / "execution/gtrade_order_status.json",
        settings_data_dir / "execution/ostium_order_status.json",
        settings_data_dir / "paper/positions.parquet",
    ]
    if any(path.exists() for path in source_paths):
        return True
    return latest_positions_sidecar(settings_data_dir / "raw/sidecar/ostium") is not None


def _refresh_execution_lineage_artifacts(
    settings_data_dir: Path,
    *,
    only_if_sources_exist: bool = False,
) -> dict[str, tuple[Path, Path, str]]:
    if only_if_sources_exist and not _has_target_free_execution_observation_sources(settings_data_dir):
        return {}
    execution_snapshot_out, execution_snapshot_summary_out, execution_snapshot_text = _write_execution_snapshot(
        settings_data_dir
    )
    execution_comparison_out, execution_comparison_summary_out, execution_comparison_text = _write_execution_venue_comparison(
        settings_data_dir
    )
    execution_diagnostics_out, execution_diagnostics_summary_out, execution_diagnostics_text = _write_execution_venue_diagnostics(
        settings_data_dir
    )
    gap_history_out, gap_history_summary_out, gap_history_text = _write_execution_gap_history(settings_data_dir)
    state_comparison_out, state_comparison_summary_out, state_comparison_text = _write_execution_state_comparison_history(
        settings_data_dir
    )
    snapshot_drift_out, snapshot_drift_summary_out, snapshot_drift_text = _write_execution_snapshot_drift_history(
        settings_data_dir
    )
    drift_overview_out, drift_overview_summary_out, drift_overview_text = _write_execution_drift_overview(
        settings_data_dir
    )
    return {
        "execution_snapshot": (execution_snapshot_out, execution_snapshot_summary_out, execution_snapshot_text),
        "execution_comparison": (execution_comparison_out, execution_comparison_summary_out, execution_comparison_text),
        "execution_diagnostics": (execution_diagnostics_out, execution_diagnostics_summary_out, execution_diagnostics_text),
        "execution_gap_history": (gap_history_out, gap_history_summary_out, gap_history_text),
        "execution_state_comparison_history": (
            state_comparison_out,
            state_comparison_summary_out,
            state_comparison_text,
        ),
        "execution_snapshot_drift_history": (
            snapshot_drift_out,
            snapshot_drift_summary_out,
            snapshot_drift_text,
        ),
        "execution_drift_overview": (drift_overview_out, drift_overview_summary_out, drift_overview_text),
    }


def _execution_read_only_surface_for_venue(
    settings_data_dir: Path,
    venue: str,
    *,
    state_path: Path | None = None,
    fills_limit: int = 20,
    order_limit: int = 20,
) -> dict[str, object]:
    def _float_or_none(value: object) -> float | None:
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _int_or_none(value: object) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None

    def _timestamp_ms_or_none(value: object) -> int | None:
        if hasattr(value, "timestamp"):
            return int(value.timestamp() * 1000)
        if isinstance(value, str):
            try:
                return int(datetime.fromisoformat(value).timestamp() * 1000)
            except ValueError:
                return None
        return None

    adapter = _adapter_for_venue(settings_data_dir, venue)
    balance = adapter.read_balance()
    positions = adapter.read_positions()
    fills = adapter.read_fills(limit=fills_limit)
    order_statuses = adapter.read_order_statuses(limit=order_limit)
    health = adapter.healthcheck()
    store = _state_store(settings_data_dir, state_path)
    payload = store.get_json("paper_positions")
    internal_positions = (
        [
            PaperPosition.model_validate(item)
            for item in payload
            if isinstance(item, dict) and str(item.get("venue", "")).lower() == venue
        ]
        if isinstance(payload, list)
        else []
    )
    reconciliation = reconcile_positions(internal_positions, positions)
    latest_fill = fills[0].__dict__ if fills else {}
    latest_order_status = order_statuses[0].__dict__ if order_statuses else {}
    positions_server_time_ms = None
    positions_notional_usd_total = None
    positions_unrealized_pnl_usd_total = None
    positions_collateral_used_usd_total = None
    positions_max_withdrawable_usd_total = None
    positions_average_leverage = None
    positions_latest_open_timestamp_ms = None
    positions_total_quantity = None
    positions_total_realized_pnl = None
    positions_latest_updated_at = None
    if venue == "gtrade":
        positions_path = settings_data_dir / "paper/positions.parquet"
        if positions_path.exists():
            frame = pl.read_parquet(positions_path).filter(
                pl.col("venue").cast(pl.Utf8).str.to_lowercase() == venue
            )
            if frame.height:
                positions_total_quantity = float(frame["quantity"].sum()) if "quantity" in frame.columns else None
                positions_total_realized_pnl = (
                    float(frame["realized_pnl"].sum()) if "realized_pnl" in frame.columns else None
                )
                if {"quantity", "avg_entry_price"} <= set(frame.columns):
                    positions_notional_usd_total = float(
                        (frame["quantity"] * frame["avg_entry_price"]).sum()
                    )
                if "opened_at" in frame.columns:
                    latest_opened = frame["opened_at"].max()
                    if latest_opened is not None:
                        positions_latest_open_timestamp_ms = _timestamp_ms_or_none(latest_opened)
                if "updated_at" in frame.columns:
                    latest_updated = frame["updated_at"].max()
                    if latest_updated is not None:
                        positions_latest_updated_at = (
                            latest_updated.isoformat()
                            if hasattr(latest_updated, "isoformat")
                            else str(latest_updated)
                        )
    if venue == "ostium":
        positions_path = latest_positions_sidecar(settings_data_dir / "raw/sidecar/ostium")
        if positions_path is not None:
            payload = read_json(positions_path)
            if isinstance(payload, dict):
                positions_rows = payload.get("positions", [])
                if isinstance(positions_rows, list):
                    notional_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("notional_usd"))]
                        if value is not None
                    ]
                    unrealized_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("unrealized_pnl_usd"))]
                        if value is not None
                    ]
                    collateral_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("collateral_used_usd"))]
                        if value is not None
                    ]
                    withdrawable_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("max_withdrawable_usd"))]
                        if value is not None
                    ]
                    leverage_values = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_float_or_none(item.get("leverage"))]
                        if value is not None
                    ]
                    open_timestamps = [
                        value
                        for item in positions_rows
                        if isinstance(item, dict)
                        for value in [_int_or_none(item.get("open_timestamp_ms"))]
                        if value is not None
                    ]
                    positions_notional_usd_total = (
                        sum(notional_values) if notional_values else None
                    )
                    positions_unrealized_pnl_usd_total = (
                        sum(unrealized_values) if unrealized_values else None
                    )
                    positions_collateral_used_usd_total = (
                        sum(collateral_values) if collateral_values else None
                    )
                    positions_max_withdrawable_usd_total = (
                        sum(withdrawable_values) if withdrawable_values else None
                    )
                    positions_average_leverage = (
                        sum(leverage_values) / len(leverage_values)
                        if leverage_values
                        else None
                    )
                    positions_latest_open_timestamp_ms = (
                        max(open_timestamps) if open_timestamps else None
                    )
                positions_server_time_ms = _int_or_none(payload.get("server_time_ms"))
    return {
        "venue": venue,
        "balance_snapshot_exists": health.get("balance_snapshot_exists"),
        "positions_snapshot_exists": health.get("positions_snapshot_exists"),
        "fills_snapshot_exists": health.get("fills_snapshot_exists"),
        "order_status_snapshot_exists": health.get("order_status_snapshot_exists"),
        "currency": balance.get("currency"),
        "equity": balance.get("equity"),
        "available_cash": balance.get("available_cash"),
        "margin_used": balance.get("margin_used"),
        "notional_usd": balance.get("notional_usd"),
        "unrealized_pnl": balance.get("unrealized_pnl"),
        "cumulative_rollover_usd": balance.get("cumulative_rollover_usd"),
        "fills_count": len(fills),
        "latest_fill_id": latest_fill.get("fill_id"),
        "latest_fill_status": latest_fill.get("status"),
        "order_status_count": len(order_statuses),
        "latest_order_id": latest_order_status.get("order_id"),
        "latest_order_status": latest_order_status.get("status"),
        "positions_count": len(positions),
        "positions_server_time_ms": positions_server_time_ms,
        "positions_notional_usd_total": positions_notional_usd_total,
        "positions_unrealized_pnl_usd_total": positions_unrealized_pnl_usd_total,
        "positions_collateral_used_usd_total": positions_collateral_used_usd_total,
        "positions_max_withdrawable_usd_total": positions_max_withdrawable_usd_total,
        "positions_average_leverage": positions_average_leverage,
        "positions_latest_open_timestamp_ms": positions_latest_open_timestamp_ms,
        "positions_total_quantity": positions_total_quantity,
        "positions_total_realized_pnl": positions_total_realized_pnl,
        "positions_latest_updated_at": positions_latest_updated_at,
        "reconcile_matched": reconciliation.matched,
        "reconcile_missing_in_adapter_count": len(reconciliation.missing_in_adapter),
        "reconcile_missing_in_internal_count": len(reconciliation.missing_in_internal),
    }


def _write_execution_read_only_surfaces(
    settings_data_dir: Path,
    *,
    state_path: Path | None = None,
) -> tuple[Path, Path, str]:
    venues = ["gtrade", "ostium"]
    venue_surfaces = [
        _execution_read_only_surface_for_venue(
            settings_data_dir,
            venue,
            state_path=state_path,
        )
        for venue in venues
    ]
    out = settings_data_dir / "reports/execution_read_only_surfaces.md"
    summary_out = settings_data_dir / "ops/execution_read_only_surfaces_summary.json"
    text = build_execution_read_only_surfaces_report(
        venue_surfaces=venue_surfaces,
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_phase_gate_review(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/phase_gate_review.md"
    summary_out = settings_data_dir / "ops/phase_gate_review_summary.json"
    text = build_phase_gate_review(
        settings_data_dir,
        schema_root=Path(__file__).resolve().parents[2] / "schemas",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        remediation_evaluator_summary_path=settings_data_dir / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_planner(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_planner.md"
    summary_out = settings_data_dir / "ops/remediation_planner_summary.json"
    text = build_remediation_planner(
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        runbook_summary_path=settings_data_dir / "ops/paper_operations_runbook_summary.json",
        remediation_evaluator_summary_path=settings_data_dir / "ops/remediation_evaluator_summary.json",
        remediation_command_results_summary_path=settings_data_dir / "ops/remediation_command_results_summary.json",
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_execution_plan(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_execution_plan.md"
    summary_out = settings_data_dir / "ops/remediation_execution_plan_summary.json"
    text = build_remediation_execution_plan(
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_session(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_session.md"
    summary_out = settings_data_dir / "ops/remediation_session_summary.json"
    text = build_remediation_session(
        remediation_execution_plan_summary_path=settings_data_dir / "ops/remediation_execution_plan_summary.json",
        remediation_command_results_summary_path=settings_data_dir / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_session_checkpoint(
    settings_data_dir: Path,
    *,
    action_key: str | None = None,
    result: str | None = None,
    note: str | None = None,
    evidence_path: str | None = None,
    observed_signal: str | None = None,
    stdout_summary: str | None = None,
    stderr_summary: str | None = None,
    exit_code: int | None = None,
) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_session_checkpoint.md"
    summary_out = settings_data_dir / "ops/remediation_session_checkpoint_summary.json"
    text = build_remediation_session_checkpoint(
        remediation_session_summary_path=settings_data_dir / "ops/remediation_session_summary.json",
        checkpoint_summary_path=summary_out,
        remediation_command_results_summary_path=settings_data_dir / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
        action_key=action_key,
        result=result,
        note=note,
        evidence_path=evidence_path,
        observed_signal=observed_signal,
        stdout_summary=stdout_summary,
        stderr_summary=stderr_summary,
        exit_code=exit_code,
    )
    return out, summary_out, text


def _write_remediation_scoreboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_scoreboard.md"
    summary_out = settings_data_dir / "ops/remediation_scoreboard_summary.json"
    text = build_remediation_scoreboard(
        remediation_session_checkpoint_summary_path=settings_data_dir / "ops/remediation_session_checkpoint_summary.json",
        remediation_command_results_summary_path=settings_data_dir / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_evaluator(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_evaluator.md"
    summary_out = settings_data_dir / "ops/remediation_evaluator_summary.json"
    text = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=settings_data_dir / "ops/remediation_session_checkpoint_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_evidence(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_evidence.md"
    summary_out = settings_data_dir / "ops/remediation_evidence_summary.json"
    text = build_remediation_evidence(
        remediation_session_checkpoint_summary_path=settings_data_dir / "ops/remediation_session_checkpoint_summary.json",
        remediation_evaluator_summary_path=settings_data_dir / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_command_results(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_command_results.md"
    summary_out = settings_data_dir / "ops/remediation_command_results_summary.json"
    text = build_remediation_command_results(
        remediation_session_checkpoint_summary_path=settings_data_dir / "ops/remediation_session_checkpoint_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_operations_bundle(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_bundle_manifest.md"
    manifest_out = settings_data_dir / "ops/operations_bundle_manifest.json"
    text = build_operations_bundle_manifest(
        monitoring_summary_path=settings_data_dir / "ops/monitoring_status.json",
        ops_review_summary_path=settings_data_dir / "ops/ops_review_summary.json",
        dashboard_summary_path=settings_data_dir / "ops/operations_dashboard_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        runbook_summary_path=settings_data_dir / "ops/paper_operations_runbook_summary.json",
        paper_cycle_history_summary_path=settings_data_dir / "ops/paper_cycle_history_summary.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        manifest_path=manifest_out,
    )
    return out, manifest_out, text


def _write_operations_timeline(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_timeline_report.md"
    summary_out = settings_data_dir / "ops/operations_timeline_summary.json"
    text = build_operations_timeline_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_operations_audit_pack(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_audit_pack.md"
    manifest_out = settings_data_dir / "ops/operations_audit_pack.json"
    text = build_operations_audit_pack(
        bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        timeline_summary_path=settings_data_dir / "ops/operations_timeline_summary.json",
        cycle_history_summary_path=settings_data_dir / "ops/paper_cycle_history_summary.json",
        runbook_summary_path=settings_data_dir / "ops/paper_operations_runbook_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        manifest_path=manifest_out,
    )
    return out, manifest_out, text


def _write_audit_timeline(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_timeline_report.md"
    summary_out = settings_data_dir / "ops/audit_timeline_summary.json"
    text = build_audit_timeline_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_audit_dashboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_dashboard.md"
    summary_out = settings_data_dir / "ops/audit_dashboard_summary.json"
    text = build_audit_dashboard(
        bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        audit_pack_path=settings_data_dir / "ops/operations_audit_pack.json",
        audit_timeline_summary_path=settings_data_dir / "ops/audit_timeline_summary.json",
        audit_bundle_history_summary_path=settings_data_dir / "ops/audit_bundle_history_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_audit_bundle(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_bundle_manifest.md"
    manifest_out = settings_data_dir / "ops/audit_bundle_manifest.json"
    text = build_audit_bundle_manifest(
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_timeline_summary_path=settings_data_dir / "ops/audit_timeline_summary.json",
        audit_pack_path=settings_data_dir / "ops/operations_audit_pack.json",
        audit_bundle_history_summary_path=settings_data_dir / "ops/audit_bundle_history_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        manifest_path=manifest_out,
    )
    return out, manifest_out, text


def _write_audit_bundle_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_bundle_history_report.md"
    summary_out = settings_data_dir / "ops/audit_bundle_history_summary.json"
    text = build_audit_bundle_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _latest_live_evidence_summary_path() -> Path | None:
    summaries_root = Path("logs/live_evidence/summaries")
    paths = sorted(summaries_root.glob("live_evidence_summary_*.json"))
    return paths[-1] if paths else None


def _write_current_state_index(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/current_state_index.md"
    summary_out = settings_data_dir / "ops/current_state_index.json"
    text = build_current_state_index(
        operations_dashboard_summary_path=settings_data_dir / "ops/operations_dashboard_summary.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_manifest_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        backtest_metrics_summary_path=settings_data_dir / "research/backtest_metrics_summary.json",
        live_evidence_summary_path=_latest_live_evidence_summary_path(),
        research_quality_report_path=settings_data_dir / "research/research_quality_report.md",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_readiness_snapshot(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/readiness_snapshot.md"
    summary_out = settings_data_dir / "ops/readiness_snapshot.json"
    text = build_readiness_snapshot(
        current_state_index_path=settings_data_dir / "ops/current_state_index.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        backtest_metrics_summary_path=settings_data_dir / "research/backtest_metrics_summary.json",
        live_evidence_summary_path=_latest_live_evidence_summary_path(),
        operations_dashboard_summary_path=settings_data_dir / "ops/operations_dashboard_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _run_paper_step(
    settings_data_dir: Path,
    *,
    state_path: Path | None,
    signals_path: Path | None,
) -> object:
    return run_paper_step(
        settings_data_dir,
        state_path=state_path or (settings_data_dir / "state/marketlens.sqlite"),
        signals_path=signals_path,
    )


def _append_paper_operations_cycle_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    monitoring_status: str,
    orders_count: int,
    fills_count: int,
    open_positions: int,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="paper_operations_cycle",
        mode="paper",
        command="uv run sis paper-operations-cycle",
        status="completed" if monitoring_status == "ok" else monitoring_status,
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"orders={orders_count}",
            f"fills={fills_count}",
            f"open_positions={open_positions}",
            f"monitoring_status={monitoring_status}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_operations_snapshot_manifest(
    settings_data_dir: Path,
    *,
    manifest_path: Path,
    overall_status: str | None,
    cycle_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="operations_snapshot",
        mode="ops",
        command="uv run sis operations-bundle",
        status=overall_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(manifest_path)],
        notes=[
            f"overall_status={overall_status}",
            f"cycle_count={cycle_count}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_operations_audit_snapshot_manifest(
    settings_data_dir: Path,
    *,
    manifest_path: Path,
    overall_status: str | None,
    timeline_latest_operation: str | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="operations_audit_snapshot",
        mode="ops",
        command="uv run sis operations-audit-pack",
        status=overall_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(manifest_path)],
        notes=[
            f"overall_status={overall_status}",
            f"timeline_latest_operation={timeline_latest_operation}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_audit_bundle_snapshot_manifest(
    settings_data_dir: Path,
    *,
    manifest_path: Path,
    overall_status: str | None,
    timeline_latest_operation: str | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="audit_bundle_snapshot",
        mode="ops",
        command="uv run sis audit-bundle",
        status=overall_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(manifest_path)],
        notes=[
            f"overall_status={overall_status}",
            f"timeline_latest_operation={timeline_latest_operation}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_planner_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    planner_status: str | None,
    rerun_trend: str | None,
    next_best_command: str | None,
    next_feedback_priority_reason: str | None,
    planned_step_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_planner_dry_run",
        mode="ops",
        command="uv run sis remediation-planner",
        status=planner_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"planner_status={planner_status}",
            f"rerun_trend={rerun_trend}",
            f"planned_step_count={planned_step_count}",
            f"next_best_command={next_best_command}",
            f"next_feedback_priority_reason={next_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_execution_plan_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    execution_plan_status: str | None,
    next_action_command: str | None,
    next_action_feedback_priority_reason: str | None,
    planned_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_execution_plan_dry_run",
        mode="ops",
        command="uv run sis remediation-execution-plan",
        status=execution_plan_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"execution_plan_status={execution_plan_status}",
            f"planned_action_count={planned_action_count}",
            f"next_action_command={next_action_command}",
            f"next_action_feedback_priority_reason={next_action_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_session_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    session_status: str | None,
    next_pending_command: str | None,
    next_pending_stage_signal_confidence: str | None,
    next_pending_feedback_priority_reason: str | None,
    pending_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_session_dry_run",
        mode="ops",
        command="uv run sis remediation-session",
        status=session_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"session_status={session_status}",
            f"pending_action_count={pending_action_count}",
            f"next_pending_command={next_pending_command}",
            f"next_pending_stage_signal_confidence={next_pending_stage_signal_confidence}",
            f"next_pending_feedback_priority_reason={next_pending_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_session_checkpoint_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    checkpoint_status: str | None,
    next_action_command: str | None,
    next_action_stage_signal_confidence: str | None,
    next_action_feedback_priority_reason: str | None,
    pending_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_session_checkpoint",
        mode="ops",
        command="uv run sis remediation-session-checkpoint",
        status=checkpoint_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"checkpoint_status={checkpoint_status}",
            f"pending_action_count={pending_action_count}",
            f"next_action_command={next_action_command}",
            f"next_action_stage_signal_confidence={next_action_stage_signal_confidence}",
            f"next_action_feedback_priority_reason={next_action_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_scoreboard_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    scoreboard_status: str | None,
    next_action_command: str | None,
    next_action_stage_signal_confidence: str | None,
    next_action_feedback_priority_reason: str | None,
    completion_rate: float | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_scoreboard",
        mode="ops",
        command="uv run sis remediation-scoreboard",
        status=scoreboard_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"scoreboard_status={scoreboard_status}",
            f"completion_rate={completion_rate}",
            f"next_action_command={next_action_command}",
            f"next_action_stage_signal_confidence={next_action_stage_signal_confidence}",
            f"next_action_feedback_priority_reason={next_action_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_evaluator_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    evaluator_status: str | None,
    next_action_key: str | None,
    auto_fail_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_evaluator",
        mode="ops",
        command="uv run sis remediation-evaluator",
        status=evaluator_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"evaluator_status={evaluator_status}",
            f"auto_fail_count={auto_fail_count}",
            f"next_action_key={next_action_key}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_evidence_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    evidence_status: str | None,
    next_manual_review_action_key: str | None,
    manual_review_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_evidence",
        mode="ops",
        command="uv run sis remediation-evidence",
        status=evidence_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"evidence_status={evidence_status}",
            f"manual_review_action_count={manual_review_action_count}",
            f"next_manual_review_action_key={next_manual_review_action_key}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_command_results_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    command_results_status: str | None,
    next_unobserved_action_key: str | None,
    missing_observation_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_command_results",
        mode="ops",
        command="uv run sis remediation-command-results",
        status=command_results_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(summary_path)],
        notes=[
            f"command_results_status={command_results_status}",
            f"missing_observation_count={missing_observation_count}",
            f"next_unobserved_action_key={next_unobserved_action_key}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_evidence_ingest_manifest(
    settings_data_dir: Path,
    *,
    checkpoint_summary_path: Path,
    action_key: str | None,
    checkpoint_status: str | None,
    exit_code: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_evidence_ingest",
        mode="ops",
        command="uv run sis remediation-evidence-ingest",
        status=checkpoint_status or "unknown",
        parent_run_id=str(parent.get("run_id")) if isinstance(parent, dict) and parent.get("run_id") else None,
        artifacts=[str(checkpoint_summary_path)],
        notes=[
            f"action_key={action_key}",
            f"checkpoint_status={checkpoint_status}",
            f"exit_code={exit_code}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


@app.command("paper-step")
def paper_step_cmd(
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
    signals_path: Path | None = typer.Option(
        None,
        "--signals-path",
        help="Optional signal CSV path. Defaults to data/research/signals.csv.",
    ),
) -> None:
    settings = get_settings()
    summary = _run_paper_step(
        settings.data_dir,
        state_path=state_path,
        signals_path=signals_path,
    )
    logger.info("written: {}", summary.orders_path)
    logger.info("written: {}", summary.fills_path)
    logger.info("written: {}", summary.positions_path)
    logger.info("written: {}", summary.daily_pnl_path)
    logger.info("written: {}", summary.report_path)
    typer.echo(f"orders={summary.orders_count}")
    typer.echo(f"fills={summary.fills_count}")
    typer.echo(f"open_positions={summary.open_positions}")
    typer.echo(f"realized_pnl={summary.realized_pnl}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("paper-report")
def paper_report_cmd() -> None:
    settings = get_settings()
    fills_path = settings.data_dir / "paper/fills.parquet"
    positions_path = settings.data_dir / "paper/positions.parquet"
    if not fills_path.exists():
        typer.echo(f"Paper fills parquet not found: {fills_path}")
        raise typer.Exit(code=2)
    fills_frame = pl.read_parquet(fills_path)
    positions_frame = pl.read_parquet(positions_path) if positions_path.exists() else pl.DataFrame()
    fills = fills_frame.to_dicts()
    positions = positions_frame.to_dicts()
    paper_last_run = StateStore(settings.data_dir / "state/marketlens.sqlite").get_json("paper_last_run")
    audit_summary = paper_last_run.get("audit") if isinstance(paper_last_run, dict) else None
    if not isinstance(audit_summary, dict):
        audit_summary = _read_audit_schedule_summary(settings.data_dir)
    latest_execution_payload = _paper_last_run_latest_execution_payload(settings.data_dir)
    out = settings.data_dir / "reports/daily_paper_report.md"
    text = build_daily_paper_report(
        fills=[PaperFill.model_validate(item) for item in fills],
        positions=[PaperPosition.model_validate(item) for item in positions],
        out_path=out,
        audit_summary=audit_summary,
        phase_gate_summary=_paper_last_run_phase_gate_summary(settings.data_dir),
        readiness_summary=_paper_last_run_readiness_summary(settings.data_dir),
        **latest_execution_payload,
        execution_gap_history_summary=_paper_last_run_execution_gap_history_summary(
            settings.data_dir
        ),
        execution_state_comparison_summary=_paper_last_run_execution_state_comparison_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_paper_last_run_execution_snapshot_drift_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_paper_last_run_execution_drift_overview_summary(settings.data_dir),
    )
    logger.info("written: {}", out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("estimate-order")
def estimate_order_cmd(
    venue: str = typer.Option(..., "--venue"),
    symbol: str = typer.Option(..., "--symbol"),
    side: str = typer.Option(..., "--side"),
    quantity: float = typer.Option(1.0, "--quantity"),
    timeframe: str = typer.Option("4h", "--timeframe"),
) -> None:
    settings = get_settings()
    adapter = _adapter_for_venue(settings.data_dir, venue)
    estimate = adapter.estimate_order(
        OrderIntent(
            venue=venue,
            canonical_symbol=symbol.upper(),
            side=side.lower(),
            quantity=quantity,
            timeframe=timeframe,
        )
    )
    typer.echo(f"venue={estimate.venue}")
    typer.echo(f"symbol={estimate.canonical_symbol}")
    typer.echo(f"side={estimate.side}")
    typer.echo(f"estimated_cost_bps={estimate.estimated_cost_bps}")
    typer.echo(f"price_reference={estimate.price_reference}")
    typer.echo(f"notes={','.join(estimate.notes)}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("balance-status")
def balance_status_cmd(
    venue: str = typer.Option(..., "--venue"),
) -> None:
    settings = get_settings()
    adapter = _adapter_for_venue(settings.data_dir, venue)
    balance = adapter.read_balance()
    build_balance_status_report(
        venue=venue.strip().lower(),
        balance=balance,
        out_path=settings.data_dir / "reports/execution_balance_status.md",
        summary_path=settings.data_dir / "ops/execution_balance_status_summary.json",
    )
    for key in sorted(balance):
        typer.echo(f"{key}={balance[key]}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("fill-status")
def fill_status_cmd(
    venue: str = typer.Option(..., "--venue"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    settings = get_settings()
    adapter = _adapter_for_venue(settings.data_dir, venue)
    fills = adapter.read_fills(limit=limit)
    build_fill_status_report(
        venue=venue.strip().lower(),
        fills=fills,
        limit=limit,
        out_path=settings.data_dir / "reports/execution_fill_status.md",
        summary_path=settings.data_dir / "ops/execution_fill_status_summary.json",
    )
    typer.echo(f"venue={venue.strip().lower()}")
    typer.echo(f"fills_count={len(fills)}")
    for index, fill in enumerate(fills, start=1):
        typer.echo(f"fill_{index}_id={fill.fill_id}")
        typer.echo(f"fill_{index}_order_id={fill.order_id}")
        typer.echo(f"fill_{index}_symbol={fill.canonical_symbol}")
        typer.echo(f"fill_{index}_side={fill.side}")
        typer.echo(f"fill_{index}_quantity={fill.quantity}")
        typer.echo(f"fill_{index}_price={fill.price}")
        typer.echo(f"fill_{index}_status={fill.status}")
        typer.echo(f"fill_{index}_ts_fill={fill.ts_fill}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("execution-snapshot")
def execution_snapshot_cmd(
    venue: str | None = typer.Option(None, "--venue"),
    fills_limit: int = typer.Option(5, "--fills-limit"),
    order_limit: int = typer.Option(5, "--order-limit"),
) -> None:
    settings = get_settings()
    out, summary_out, text = _write_execution_snapshot(
        settings.data_dir,
        venue=venue,
        fills_limit=fills_limit,
        order_limit=order_limit,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("execution-venue-comparison")
def execution_venue_comparison_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_execution_venue_comparison(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("execution-venue-diagnostics")
def execution_venue_diagnostics_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_execution_venue_diagnostics(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("order-status")
def order_status_cmd(
    venue: str = typer.Option(..., "--venue"),
    order_id: str = typer.Option(..., "--order-id"),
) -> None:
    settings = get_settings()
    adapter = _adapter_for_venue(settings.data_dir, venue)
    status = adapter.read_order_status(order_id)
    build_order_status_report(
        status=status,
        out_path=settings.data_dir / "reports/execution_order_status.md",
        summary_path=settings.data_dir / "ops/execution_order_status_summary.json",
    )
    typer.echo(f"venue={status.venue}")
    typer.echo(f"order_id={status.order_id}")
    typer.echo(f"status={status.status}")
    typer.echo(f"symbol={status.canonical_symbol}")
    typer.echo(f"side={status.side}")
    typer.echo(f"quantity={status.quantity}")
    typer.echo(f"notes={','.join(status.notes)}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("cancel-order")
def cancel_order_cmd(
    venue: str = typer.Option(..., "--venue"),
    order_id: str = typer.Option(..., "--order-id"),
) -> None:
    settings = get_settings()
    adapter = _adapter_for_venue(settings.data_dir, venue)
    result = adapter.cancel_order(order_id)
    build_action_status_report(
        title="Execution Cancel Order",
        report_key="cancel_order_report_path",
        result=result,
        out_path=settings.data_dir / "reports/execution_cancel_order.md",
        summary_path=settings.data_dir / "ops/execution_cancel_order_summary.json",
    )
    typer.echo(f"venue={result.venue}")
    typer.echo(f"action={result.action}")
    typer.echo(f"target={result.target}")
    typer.echo(f"success={result.success}")
    typer.echo(f"status={result.status}")
    typer.echo(f"notes={','.join(result.notes)}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("close-position")
def close_position_cmd(
    venue: str = typer.Option(..., "--venue"),
    symbol: str = typer.Option(..., "--symbol"),
    side: str | None = typer.Option(None, "--side"),
) -> None:
    settings = get_settings()
    adapter = _adapter_for_venue(settings.data_dir, venue)
    result = adapter.close_position(symbol.upper(), side)
    build_action_status_report(
        title="Execution Close Position",
        report_key="close_position_report_path",
        result=result,
        out_path=settings.data_dir / "reports/execution_close_position.md",
        summary_path=settings.data_dir / "ops/execution_close_position_summary.json",
    )
    typer.echo(f"venue={result.venue}")
    typer.echo(f"action={result.action}")
    typer.echo(f"target={result.target}")
    typer.echo(f"success={result.success}")
    typer.echo(f"status={result.status}")
    typer.echo(f"notes={','.join(result.notes)}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("reconcile-positions")
def reconcile_positions_cmd(
    venue: str = typer.Option(..., "--venue"),
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
) -> None:
    settings = get_settings()
    store = _state_store(settings.data_dir, state_path)
    payload = store.get_json("paper_positions")
    internal_positions = [PaperPosition.model_validate(item) for item in payload] if isinstance(payload, list) else []
    adapter = _adapter_for_venue(settings.data_dir, venue)
    result = reconcile_positions(internal_positions, adapter.read_positions())
    out = {
        "venue": venue,
        "matched": result.matched,
        "missing_in_adapter": result.missing_in_adapter,
        "missing_in_internal": result.missing_in_internal,
    }
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    store.record_reconciliation(run_id, datetime.now(timezone.utc).isoformat(), out)
    build_reconcile_positions_report(
        venue=venue.strip().lower(),
        result=result,
        run_id=run_id,
        state_store_path=str(store.path),
        out_path=settings.data_dir / "reports/execution_reconcile_positions.md",
        summary_path=settings.data_dir / "ops/execution_reconcile_positions_summary.json",
    )
    typer.echo(f"matched={result.matched}")
    typer.echo(f"missing_in_adapter={len(result.missing_in_adapter)}")
    typer.echo(f"missing_in_internal={len(result.missing_in_internal)}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("healthcheck")
def healthcheck_cmd(
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
    current_pnl: float = typer.Option(0.0, "--current-pnl"),
    daily_loss_limit: float = typer.Option(100.0, "--daily-loss-limit"),
    current_exposure: float = typer.Option(0.0, "--current-exposure"),
    max_exposure: float = typer.Option(2.0, "--max-exposure"),
) -> None:
    settings = get_settings()
    store = _state_store(settings.data_dir, state_path)
    kill_switch = KillSwitch(settings.data_dir / "state/kill_switch.flag")
    loss_status = evaluate_daily_loss_limit(current_pnl, daily_loss_limit)
    exposure_status = evaluate_max_exposure(current_exposure, max_exposure)
    health = build_healthcheck(
        kill_switch=kill_switch,
        decision_summary_path=settings.data_dir / "research/decision_summary.json",
        audit_dashboard_summary_path=settings.data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings.data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings.data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings.data_dir / "ops/phase_gate_review_summary.json",
        execution_summary_path=settings.data_dir / "ops/execution_snapshot_summary.json",
        execution_comparison_summary_path=settings.data_dir / "ops/execution_venue_comparison_summary.json",
        execution_diagnostics_summary_path=settings.data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings.data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_summary_path=settings.data_dir / "ops/execution_state_comparison_history_summary.json",
        execution_snapshot_drift_summary_path=settings.data_dir / "ops/execution_snapshot_drift_history_summary.json",
        execution_drift_overview_summary_path=settings.data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings.data_dir / "ops/readiness_snapshot.json",
        reconciliation_store_present=store.latest_reconciliation() is not None,
    )
    build_healthcheck_report(
        health=health,
        daily_loss_status=loss_status,
        exposure_status=exposure_status,
        out_path=settings.data_dir / "reports/ops_healthcheck.md",
        summary_path=settings.data_dir / "ops/ops_healthcheck_summary.json",
    )
    typer.echo(f"status={health['status']}")
    typer.echo(f"kill_switch_enabled={health['kill_switch_enabled']}")
    typer.echo(f"decision_summary_exists={health['decision_summary_exists']}")
    _echo_audit_summary(health)
    _echo_phase_gate_summary(health)
    typer.echo(f"execution_drift_overview_status={health.get('execution_drift_overview_status')}")
    typer.echo(
        "execution_drift_overview_diagnostics_alignment_match="
        f"{health.get('execution_drift_overview_diagnostics_alignment_match')}"
    )
    typer.echo(
        "execution_drift_overview_state_comparison_mismatching_count="
        f"{health.get('execution_drift_overview_state_comparison_mismatching_count')}"
    )
    typer.echo(
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
        f"{health.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
    )
    typer.echo(f"readiness_next_phase_candidate={health.get('readiness_next_phase_candidate')}")
    typer.echo(f"readiness_execution_ready={health.get('readiness_execution_ready')}")
    typer.echo(f"reconciliation_store_present={health['reconciliation_store_present']}")
    typer.echo(f"daily_loss_allowed={loss_status.allowed}")
    typer.echo(f"daily_loss_reason={loss_status.reason}")
    typer.echo(f"exposure_allowed={exposure_status.allowed}")
    typer.echo(f"exposure_reason={exposure_status.reason}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("monitoring-status")
def monitoring_status_cmd(
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
) -> None:
    settings = get_settings()
    out, snapshot = _write_monitoring_snapshot(settings.data_dir, state_path)
    logger.info("written: {}", out)
    typer.echo(f"status={snapshot['status']}")
    typer.echo(f"decision_summary_exists={snapshot['decision_summary_exists']}")
    typer.echo(f"weekly_review_exists={snapshot['weekly_review_exists']}")
    typer.echo(f"daily_pnl_exists={snapshot['daily_pnl_exists']}")
    typer.echo(f"operation_chain_exists={snapshot['operation_chain_exists']}")
    _echo_audit_summary(snapshot)
    _echo_phase_gate_summary(snapshot)
    typer.echo(f"execution_drift_overview_status={snapshot.get('execution_drift_overview_status')}")
    typer.echo(
        "execution_drift_overview_diagnostics_alignment_match="
        f"{snapshot.get('execution_drift_overview_diagnostics_alignment_match')}"
    )
    typer.echo(
        "execution_drift_overview_state_comparison_mismatching_count="
        f"{snapshot.get('execution_drift_overview_state_comparison_mismatching_count')}"
    )
    typer.echo(
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
        f"{snapshot.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
    )
    typer.echo(f"readiness_next_phase_candidate={snapshot.get('readiness_next_phase_candidate')}")
    typer.echo(f"readiness_execution_ready={snapshot.get('readiness_execution_ready')}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("kill-switch")
def kill_switch_cmd(
    enable: bool = typer.Option(False, "--enable"),
    disable: bool = typer.Option(False, "--disable"),
    reason: str = typer.Option("manual", "--reason"),
) -> None:
    if enable and disable:
        typer.echo("Choose either --enable or --disable, not both.")
        raise typer.Exit(code=2)
    settings = get_settings()
    switch = KillSwitch(settings.data_dir / "state/kill_switch.flag")
    if enable:
        switch.enable(reason)
    elif disable:
        switch.disable()
    status = switch.status()
    build_kill_switch_report(
        status=status,
        out_path=settings.data_dir / "reports/ops_kill_switch.md",
        summary_path=settings.data_dir / "ops/ops_kill_switch_summary.json",
    )
    typer.echo(f"enabled={status['enabled']}")
    typer.echo(f"path={status['path']}")
    settings = get_settings()
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("schedule-run")
def schedule_run_cmd(
    run_type: str = typer.Option(..., "--run-type"),
    command: str = typer.Option(..., "--command"),
    at: str | None = typer.Option(None, "--at", help="ISO datetime for the scheduled run."),
    every_minutes: int | None = typer.Option(None, "--every-minutes", help="Interval schedule in minutes."),
) -> None:
    if bool(at) == bool(every_minutes):
        typer.echo("Choose exactly one of --at or --every-minutes.")
        raise typer.Exit(code=2)
    settings = get_settings()
    if at is not None:
        scheduled_for = datetime.fromisoformat(at.replace("Z", "+00:00"))
        run = schedule_run(run_type=run_type, scheduled_for=scheduled_for, command=command)
    else:
        run = next_interval_run(run_type=run_type, every_minutes=every_minutes or 0, command=command)
    out = write_schedule_with_audit(
        settings.data_dir / "ops/scheduled_run.json",
        run,
        audit_summary=_read_audit_schedule_summary(settings.data_dir),
        phase_gate_summary=_read_phase_gate_schedule_summary(settings.data_dir),
        execution_summary=_read_execution_schedule_summary(settings.data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings.data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings.data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(settings.data_dir),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings.data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings.data_dir),
    )
    build_schedule_run_report(
        run=run,
        scheduled_run_path=str(out),
        out_path=settings.data_dir / "reports/ops_scheduled_run.md",
        summary_path=settings.data_dir / "ops/ops_scheduled_run_summary.json",
    )
    logger.info("written: {}", out)
    typer.echo(f"run_type={run.run_type}")
    typer.echo(f"scheduled_for={run.scheduled_for.isoformat()}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("render-alert")
def render_alert_cmd(
    level: str = typer.Option(..., "--level"),
    title: str = typer.Option(..., "--title"),
    body: str = typer.Option(..., "--body"),
    source: str = typer.Option("codex", "--source"),
) -> None:
    settings = get_settings()
    out = write_alert(
        settings.data_dir / "alerts/latest_alert.txt",
        level=level,
        title=title,
        body=body,
        source=source,
    )
    rendered_text = out.read_text(encoding="utf-8")
    build_alert_report(
        level=level,
        title=title,
        body=body,
        source=source,
        alert_path=str(out),
        rendered_text=rendered_text,
        out_path=settings.data_dir / "reports/ops_alert.md",
        summary_path=settings.data_dir / "ops/ops_alert_summary.json",
    )
    logger.info("written: {}", out)
    typer.echo(rendered_text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("weekly-review")
def weekly_review_cmd() -> None:
    settings = get_settings()
    out, text = _write_weekly_review(settings.data_dir)
    logger.info("written: {}", out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("daemon-manifest")
def daemon_manifest_cmd(
    mode: str = typer.Option("paper", "--mode"),
    command: str = typer.Option("uv run sis paper-step", "--command"),
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
) -> None:
    settings = get_settings()
    manifest = create_daemon_manifest(
        mode=mode,
        command=command,
        state_store_path=state_path or (settings.data_dir / "state/marketlens.sqlite"),
        notes=["foundation_only", "non_daemon_runtime"],
    )
    out = write_daemon_manifest(settings.data_dir / "ops/daemon_manifest.json", manifest)
    _write_daemon_manifest_artifacts(settings.data_dir)
    logger.info("written: {}", out)
    typer.echo(f"run_id={manifest.run_id}")
    typer.echo(f"mode={manifest.mode}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("daemon-dry-run")
def daemon_dry_run_cmd(
    mode: str = typer.Option("paper", "--mode"),
    command: str = typer.Option("uv run sis paper-step", "--command"),
    every_minutes: int = typer.Option(30, "--every-minutes"),
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
) -> None:
    settings = get_settings()
    _refresh_execution_lineage_artifacts(settings.data_dir, only_if_sources_exist=True)
    _write_execution_read_only_surfaces(settings.data_dir, state_path=state_path)
    result = run_daemon_dry_run(
        data_dir=settings.data_dir,
        mode=mode,
        command=command,
        state_store_path=state_path or (settings.data_dir / "state/marketlens.sqlite"),
        every_minutes=every_minutes,
        kill_switch=KillSwitch(settings.data_dir / "state/kill_switch.flag"),
        decision_summary_path=settings.data_dir / "research/decision_summary.json",
        audit_dashboard_summary_path=settings.data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings.data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings.data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings.data_dir / "ops/phase_gate_review_summary.json",
        execution_summary=_read_execution_schedule_summary(settings.data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings.data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings.data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(settings.data_dir),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings.data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings.data_dir),
    )
    logger.info("written: {}", result.schedule_path)
    logger.info("written: {}", result.daemon_manifest_path)
    logger.info("written: {}", result.dry_run_snapshot_path)
    logger.info("appended: {}", result.operation_chain_path)
    typer.echo(f"run_id={result.run_id}")
    typer.echo(f"status={result.status}")
    typer.echo(f"scheduled_for={result.scheduled_for}")
    typer.echo(f"operation_chain={result.operation_chain_path}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("export-state")
def export_state_cmd(
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
) -> None:
    settings = get_settings()
    store = _state_store(settings.data_dir, state_path)
    out = export_state_snapshot(store, settings.data_dir / "state/state_snapshot.json")
    logger.info("written: {}", out)
    typer.echo(str(out))
    payload = read_json(out)
    if isinstance(payload, dict):
        _write_state_export_artifacts(settings.data_dir, state_store_path=store.path)
        audit = payload.get("audit_summary")
        if isinstance(audit, dict):
            _echo_audit_summary(audit)
        phase_gate = payload.get("phase_gate_summary")
        if isinstance(phase_gate, dict):
            _echo_phase_gate_summary(normalize_phase_gate_summary(phase_gate))
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("restore-state")
def restore_state_cmd(
    snapshot_path: Path = typer.Option(..., "--snapshot-path"),
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
) -> None:
    settings = get_settings()
    store = _state_store(settings.data_dir, state_path)
    restore_state_snapshot(store, snapshot_path)
    payload = read_json(snapshot_path)
    if isinstance(payload, dict):
        _write_state_restore_artifacts(
            settings.data_dir,
            snapshot_path=snapshot_path,
            state_store_path=store.path,
            restored=True,
        )
    typer.echo("restored=true")
    if isinstance(payload, dict):
        audit = payload.get("audit_summary")
        if isinstance(audit, dict):
            _echo_audit_summary(audit)
        phase_gate = payload.get("phase_gate_summary")
        if isinstance(phase_gate, dict):
            _echo_phase_gate_summary(normalize_phase_gate_summary(phase_gate))
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("lifecycle-report")
def lifecycle_report_cmd() -> None:
    settings = get_settings()
    out, text = _write_lifecycle_report(settings.data_dir)
    logger.info("written: {}", out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("comparison-report")
def comparison_report_cmd() -> None:
    settings = get_settings()
    out, text = _write_comparison_report(settings.data_dir)
    logger.info("written: {}", out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("ops-review")
def ops_review_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_ops_review(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("operations-dashboard")
def operations_dashboard_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_operations_dashboard(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("paper-operations-runbook")
def paper_operations_runbook_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_paper_operations_runbook(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("paper-cycle-history")
def paper_cycle_history_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_paper_cycle_history(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("execution-gap-history")
def execution_gap_history_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_execution_gap_history(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("execution-state-comparison-history")
def execution_state_comparison_history_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_execution_state_comparison_history(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("execution-snapshot-drift-history")
def execution_snapshot_drift_history_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_execution_snapshot_drift_history(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("execution-drift-overview")
def execution_drift_overview_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_execution_drift_overview(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("phase-gate-review")
def phase_gate_review_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_phase_gate_review(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-planner")
def remediation_planner_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_planner(settings.data_dir)
    payload = read_json(summary_out)
    chain_out = _append_remediation_planner_manifest(
        settings.data_dir,
        summary_path=summary_out,
        planner_status=payload.get("planner_status") if isinstance(payload, dict) else None,
        rerun_trend=(
            payload.get("planner_rerun_diff", {}).get("trend")
            if isinstance(payload, dict) and isinstance(payload.get("planner_rerun_diff"), dict)
            else None
        ),
        next_best_command=payload.get("next_best_command") if isinstance(payload, dict) else None,
        next_feedback_priority_reason=(
            payload.get("entries", [{}])[0].get("feedback_priority_reason")
            if isinstance(payload, dict) and isinstance(payload.get("entries"), list) and payload.get("entries")
            else None
        ),
        planned_step_count=payload.get("planned_step_count") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-execution-plan")
def remediation_execution_plan_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_execution_plan(settings.data_dir)
    payload = read_json(summary_out)
    chain_out = _append_remediation_execution_plan_manifest(
        settings.data_dir,
        summary_path=summary_out,
        execution_plan_status=payload.get("execution_plan_status") if isinstance(payload, dict) else None,
        next_action_command=payload.get("next_action_command") if isinstance(payload, dict) else None,
        next_action_feedback_priority_reason=(
            payload.get("actions", [{}])[0].get("feedback_priority_reason")
            if isinstance(payload, dict) and isinstance(payload.get("actions"), list) and payload.get("actions")
            else None
        ),
        planned_action_count=payload.get("planned_action_count") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-session")
def remediation_session_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_session(settings.data_dir)
    payload = read_json(summary_out)
    chain_out = _append_remediation_session_manifest(
        settings.data_dir,
        summary_path=summary_out,
        session_status=payload.get("session_status") if isinstance(payload, dict) else None,
        next_pending_command=payload.get("next_pending_command") if isinstance(payload, dict) else None,
        next_pending_stage_signal_confidence=(
            payload.get("next_pending_stage_signal_confidence")
            if isinstance(payload, dict)
            else None
        ),
        next_pending_feedback_priority_reason=(
            payload.get("next_pending_feedback_priority_reason")
            if isinstance(payload, dict)
            else None
        ),
        pending_action_count=payload.get("pending_action_count") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-session-checkpoint")
def remediation_session_checkpoint_cmd(
    action_key: str | None = typer.Option(None, "--action-key", help="Stable action key to update."),
    result: str | None = typer.Option(None, "--result", help="One of: pending, pass, fail, retry."),
    note: str | None = typer.Option(None, "--note", help="Optional operator note appended to the action."),
    evidence_path: str | None = typer.Option(None, "--evidence-path", help="Optional evidence artifact path recorded on the action."),
    observed_signal: str | None = typer.Option(None, "--observed-signal", help="Optional verification signal observed to have passed."),
    stdout_summary: str | None = typer.Option(None, "--stdout-summary", help="Optional stdout summary recorded on the action."),
    stderr_summary: str | None = typer.Option(None, "--stderr-summary", help="Optional stderr summary recorded on the action."),
    exit_code: int | None = typer.Option(None, "--exit-code", help="Optional command exit code recorded on the action."),
) -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_session_checkpoint(
        settings.data_dir,
        action_key=action_key,
        result=result,
        note=note,
        evidence_path=evidence_path,
        observed_signal=observed_signal,
        stdout_summary=stdout_summary,
        stderr_summary=stderr_summary,
        exit_code=exit_code,
    )
    payload = read_json(summary_out)
    chain_out = _append_remediation_session_checkpoint_manifest(
        settings.data_dir,
        summary_path=summary_out,
        checkpoint_status=payload.get("checkpoint_status") if isinstance(payload, dict) else None,
        next_action_command=payload.get("next_action_command") if isinstance(payload, dict) else None,
        next_action_stage_signal_confidence=(
            payload.get("next_action_stage_signal_confidence")
            if isinstance(payload, dict)
            else None
        ),
        next_action_feedback_priority_reason=(
            next(
                (
                    item.get("feedback_priority_reason")
                    for item in payload.get("actions", [])
                    if isinstance(item, dict)
                    and item.get("command") == payload.get("next_action_command")
                ),
                None,
            )
            if isinstance(payload, dict)
            else None
        ),
        pending_action_count=payload.get("pending_action_count") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-evidence-ingest")
def remediation_evidence_ingest_cmd(
    action_key: str = typer.Option(..., "--action-key", help="Stable action key to update."),
    result: str | None = typer.Option(None, "--result", help="One of: pending, pass, fail, retry."),
    note: str | None = typer.Option(None, "--note", help="Optional operator note appended to the action."),
    evidence_path: str | None = typer.Option(None, "--evidence-path", help="Optional evidence artifact path recorded on the action."),
    observed_signal: str | None = typer.Option(None, "--observed-signal", help="Optional verification signal observed to have passed."),
    stdout_summary: str | None = typer.Option(None, "--stdout-summary", help="Optional stdout summary recorded on the action."),
    stderr_summary: str | None = typer.Option(None, "--stderr-summary", help="Optional stderr summary recorded on the action."),
    exit_code: int | None = typer.Option(None, "--exit-code", help="Optional command exit code recorded on the action."),
) -> None:
    settings = get_settings()
    checkpoint_out, checkpoint_summary_out, _checkpoint_text = _write_remediation_session_checkpoint(
        settings.data_dir,
        action_key=action_key,
        result=result,
        note=note,
        evidence_path=evidence_path,
        observed_signal=observed_signal,
        stdout_summary=stdout_summary,
        stderr_summary=stderr_summary,
        exit_code=exit_code,
    )
    command_results_out, command_results_summary_out, command_results_text = _write_remediation_command_results(
        settings.data_dir
    )
    checkpoint_payload = read_json(checkpoint_summary_out)
    chain_out = _append_remediation_evidence_ingest_manifest(
        settings.data_dir,
        checkpoint_summary_path=checkpoint_summary_out,
        action_key=action_key,
        checkpoint_status=(
            checkpoint_payload.get("checkpoint_status")
            if isinstance(checkpoint_payload, dict)
            else None
        ),
        exit_code=exit_code,
    )
    logger.info("written: {}", checkpoint_out)
    logger.info("written: {}", checkpoint_summary_out)
    logger.info("written: {}", command_results_out)
    logger.info("written: {}", command_results_summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(command_results_text)
    typer.echo(f"remediation_session_checkpoint_path={checkpoint_out}")
    typer.echo(f"remediation_command_results_path={command_results_out}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-scoreboard")
def remediation_scoreboard_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_scoreboard(settings.data_dir)
    payload = read_json(summary_out)
    chain_out = _append_remediation_scoreboard_manifest(
        settings.data_dir,
        summary_path=summary_out,
        scoreboard_status=payload.get("scoreboard_status") if isinstance(payload, dict) else None,
        next_action_command=payload.get("next_action_command") if isinstance(payload, dict) else None,
        next_action_stage_signal_confidence=(
            payload.get("next_action_stage_signal_confidence")
            if isinstance(payload, dict)
            else None
        ),
        next_action_feedback_priority_reason=(
            next(
                (
                    item.get("feedback_priority_reason")
                    for item in payload.get("actions", [])
                    if isinstance(item, dict)
                    and item.get("command") == payload.get("next_action_command")
                ),
                None,
            )
            if isinstance(payload, dict)
            else None
        ),
        completion_rate=payload.get("completion_rate") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-evaluator")
def remediation_evaluator_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_evaluator(settings.data_dir)
    payload = read_json(summary_out)
    chain_out = _append_remediation_evaluator_manifest(
        settings.data_dir,
        summary_path=summary_out,
        evaluator_status=payload.get("evaluator_status") if isinstance(payload, dict) else None,
        next_action_key=payload.get("next_action_key") if isinstance(payload, dict) else None,
        auto_fail_count=payload.get("auto_fail_count") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-evidence")
def remediation_evidence_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_evidence(settings.data_dir)
    payload = read_json(summary_out)
    chain_out = _append_remediation_evidence_manifest(
        settings.data_dir,
        summary_path=summary_out,
        evidence_status=payload.get("evidence_status") if isinstance(payload, dict) else None,
        next_manual_review_action_key=(
            payload.get("next_manual_review_action_key")
            if isinstance(payload, dict)
            else None
        ),
        manual_review_action_count=(
            payload.get("manual_review_action_count")
            if isinstance(payload, dict)
            else None
        ),
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("remediation-command-results")
def remediation_command_results_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_remediation_command_results(settings.data_dir)
    payload = read_json(summary_out)
    chain_out = _append_remediation_command_results_manifest(
        settings.data_dir,
        summary_path=summary_out,
        command_results_status=(
            payload.get("command_results_status")
            if isinstance(payload, dict)
            else None
        ),
        next_unobserved_action_key=(
            payload.get("next_unobserved_action_key")
            if isinstance(payload, dict)
            else None
        ),
        missing_observation_count=(
            payload.get("missing_observation_count")
            if isinstance(payload, dict)
            else None
        ),
    )
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("operations-bundle")
def operations_bundle_cmd() -> None:
    settings = get_settings()
    out, manifest_out, text = _write_operations_bundle(settings.data_dir)
    payload = read_json(manifest_out)
    chain_out = _append_operations_snapshot_manifest(
        settings.data_dir,
        manifest_path=manifest_out,
        overall_status=payload.get("overall_status") if isinstance(payload, dict) else None,
        cycle_count=payload.get("cycle_count") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", manifest_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("operations-timeline")
def operations_timeline_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_operations_timeline(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("operations-audit-pack")
def operations_audit_pack_cmd() -> None:
    settings = get_settings()
    out, manifest_out, text = _write_operations_audit_pack(settings.data_dir)
    payload = read_json(manifest_out)
    chain_out = _append_operations_audit_snapshot_manifest(
        settings.data_dir,
        manifest_path=manifest_out,
        overall_status=payload.get("overall_status") if isinstance(payload, dict) else None,
        timeline_latest_operation=payload.get("timeline_latest_operation") if isinstance(payload, dict) else None,
    )
    logger.info("written: {}", out)
    logger.info("written: {}", manifest_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("audit-timeline")
def audit_timeline_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_audit_timeline(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("audit-dashboard")
def audit_dashboard_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_audit_dashboard(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("audit-bundle")
def audit_bundle_cmd() -> None:
    settings = get_settings()
    out, manifest_out, text = _write_audit_bundle(settings.data_dir)
    payload = read_json(manifest_out)
    chain_out = _append_audit_bundle_snapshot_manifest(
        settings.data_dir,
        manifest_path=manifest_out,
        overall_status=payload.get("overall_status") if isinstance(payload, dict) else None,
        timeline_latest_operation=payload.get("timeline_latest_operation") if isinstance(payload, dict) else None,
    )
    audit_timeline_out, audit_timeline_summary_out, _audit_timeline_text = _write_audit_timeline(settings.data_dir)
    audit_dashboard_out, audit_dashboard_summary_out, _audit_dashboard_text = _write_audit_dashboard(settings.data_dir)
    out, manifest_out, text = _write_audit_bundle(settings.data_dir)
    audit_bundle_history_out, audit_bundle_history_summary_out, _audit_bundle_history_text = _write_audit_bundle_history(
        settings.data_dir
    )
    logger.info("written: {}", out)
    logger.info("written: {}", manifest_out)
    logger.info("written: {}", audit_timeline_out)
    logger.info("written: {}", audit_timeline_summary_out)
    logger.info("written: {}", audit_dashboard_out)
    logger.info("written: {}", audit_dashboard_summary_out)
    logger.info("written: {}", audit_bundle_history_out)
    logger.info("written: {}", audit_bundle_history_summary_out)
    logger.info("appended: {}", chain_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("audit-bundle-history")
def audit_bundle_history_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_audit_bundle_history(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("current-state-index")
def current_state_index_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_current_state_index(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("readiness-snapshot")
def readiness_snapshot_cmd() -> None:
    settings = get_settings()
    out, summary_out, text = _write_readiness_snapshot(settings.data_dir)
    logger.info("written: {}", out)
    logger.info("written: {}", summary_out)
    typer.echo(text)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("refresh-operations-artifacts")
def refresh_operations_artifacts_cmd(
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
) -> None:
    settings = get_settings()
    daemon_manifest_artifacts = _write_daemon_manifest_artifacts(settings.data_dir)
    state_export_artifacts = _write_state_export_artifacts(settings.data_dir)
    state_restore_artifacts = _write_state_restore_artifacts(
        settings.data_dir,
        snapshot_path=settings.data_dir / "state/state_snapshot.json",
        restored=False,
    )
    execution_lineage = _refresh_execution_lineage_artifacts(settings.data_dir)
    execution_read_only_surfaces_out, execution_read_only_surfaces_summary_out, _execution_read_only_surfaces_text = _write_execution_read_only_surfaces(
        settings.data_dir,
        state_path=state_path,
    )
    execution_snapshot_out, execution_snapshot_summary_out, _execution_snapshot_text = execution_lineage["execution_snapshot"]
    execution_comparison_out, execution_comparison_summary_out, _execution_comparison_text = execution_lineage["execution_comparison"]
    execution_diagnostics_out, execution_diagnostics_summary_out, _execution_diagnostics_text = execution_lineage["execution_diagnostics"]
    weekly_out, _weekly_text = _write_weekly_review(settings.data_dir)
    comparison_out, _comparison_text = _write_comparison_report(settings.data_dir)
    lifecycle_out, _lifecycle_text = _write_lifecycle_report(settings.data_dir)
    monitoring_out, monitoring = _write_monitoring_snapshot(settings.data_dir, state_path)
    ops_review_out, ops_review_summary_out, _ops_review_text = _write_ops_review(settings.data_dir)
    dashboard_out, dashboard_summary_out, dashboard_text = _write_operations_dashboard(settings.data_dir)
    runbook_out, runbook_summary_out, _runbook_text = _write_paper_operations_runbook(settings.data_dir)
    cycle_history_out, cycle_history_summary_out, _cycle_history_text = _write_paper_cycle_history(settings.data_dir)
    gap_history_out, gap_history_summary_out, _gap_history_text = execution_lineage["execution_gap_history"]
    state_comparison_out, state_comparison_summary_out, _state_comparison_text = execution_lineage["execution_state_comparison_history"]
    snapshot_drift_out, snapshot_drift_summary_out, _snapshot_drift_text = execution_lineage["execution_snapshot_drift_history"]
    drift_overview_out, drift_overview_summary_out, _drift_overview_text = execution_lineage["execution_drift_overview"]
    phase_gate_out, phase_gate_summary_out, _phase_gate_text = _write_phase_gate_review(settings.data_dir)
    remediation_planner_out, remediation_planner_summary_out, _remediation_planner_text = _write_remediation_planner(
        settings.data_dir
    )
    remediation_execution_plan_out, remediation_execution_plan_summary_out, _remediation_execution_plan_text = _write_remediation_execution_plan(
        settings.data_dir
    )
    remediation_session_out, remediation_session_summary_out, _remediation_session_text = _write_remediation_session(
        settings.data_dir
    )
    remediation_session_checkpoint_out, remediation_session_checkpoint_summary_out, _remediation_session_checkpoint_text = _write_remediation_session_checkpoint(
        settings.data_dir
    )
    remediation_evaluator_out, remediation_evaluator_summary_out, _remediation_evaluator_text = _write_remediation_evaluator(
        settings.data_dir
    )
    remediation_command_results_out, remediation_command_results_summary_out, _remediation_command_results_text = _write_remediation_command_results(
        settings.data_dir
    )
    remediation_scoreboard_out, remediation_scoreboard_summary_out, _remediation_scoreboard_text = _write_remediation_scoreboard(
        settings.data_dir
    )
    remediation_evidence_out, remediation_evidence_summary_out, _remediation_evidence_text = _write_remediation_evidence(
        settings.data_dir
    )
    runbook_out, runbook_summary_out, _runbook_text = _write_paper_operations_runbook(settings.data_dir)
    phase_gate_out, phase_gate_summary_out, _phase_gate_text = _write_phase_gate_review(settings.data_dir)
    remediation_planner_out, remediation_planner_summary_out, _remediation_planner_text = _write_remediation_planner(
        settings.data_dir
    )
    remediation_execution_plan_out, remediation_execution_plan_summary_out, _remediation_execution_plan_text = _write_remediation_execution_plan(
        settings.data_dir
    )
    remediation_session_out, remediation_session_summary_out, _remediation_session_text = _write_remediation_session(
        settings.data_dir
    )
    remediation_session_checkpoint_out, remediation_session_checkpoint_summary_out, _remediation_session_checkpoint_text = _write_remediation_session_checkpoint(
        settings.data_dir
    )
    remediation_evaluator_out, remediation_evaluator_summary_out, _remediation_evaluator_text = _write_remediation_evaluator(
        settings.data_dir
    )
    remediation_command_results_out, remediation_command_results_summary_out, _remediation_command_results_text = _write_remediation_command_results(
        settings.data_dir
    )
    remediation_scoreboard_out, remediation_scoreboard_summary_out, _remediation_scoreboard_text = _write_remediation_scoreboard(
        settings.data_dir
    )
    remediation_evidence_out, remediation_evidence_summary_out, _remediation_evidence_text = _write_remediation_evidence(
        settings.data_dir
    )
    bundle_out, bundle_manifest_out, _bundle_text = _write_operations_bundle(settings.data_dir)
    timeline_out, timeline_summary_out, _timeline_text = _write_operations_timeline(settings.data_dir)
    audit_out, audit_manifest_out, _audit_text = _write_operations_audit_pack(settings.data_dir)
    audit_timeline_out, audit_timeline_summary_out, _audit_timeline_text = _write_audit_timeline(settings.data_dir)
    audit_dashboard_out, audit_dashboard_summary_out, _audit_dashboard_text = _write_audit_dashboard(settings.data_dir)
    audit_bundle_out, audit_bundle_manifest_out, _audit_bundle_text = _write_audit_bundle(settings.data_dir)
    bundle_payload = read_json(bundle_manifest_out)
    bundle_chain_out = _append_operations_snapshot_manifest(
        settings.data_dir,
        manifest_path=bundle_manifest_out,
        overall_status=bundle_payload.get("overall_status") if isinstance(bundle_payload, dict) else None,
        cycle_count=bundle_payload.get("cycle_count") if isinstance(bundle_payload, dict) else None,
    )
    audit_payload = read_json(audit_manifest_out)
    audit_chain_out = _append_operations_audit_snapshot_manifest(
        settings.data_dir,
        manifest_path=audit_manifest_out,
        overall_status=audit_payload.get("overall_status") if isinstance(audit_payload, dict) else None,
        timeline_latest_operation=audit_payload.get("timeline_latest_operation") if isinstance(audit_payload, dict) else None,
    )
    audit_bundle_payload = read_json(audit_bundle_manifest_out)
    audit_bundle_chain_out = _append_audit_bundle_snapshot_manifest(
        settings.data_dir,
        manifest_path=audit_bundle_manifest_out,
        overall_status=audit_bundle_payload.get("overall_status") if isinstance(audit_bundle_payload, dict) else None,
        timeline_latest_operation=audit_bundle_payload.get("timeline_latest_operation") if isinstance(audit_bundle_payload, dict) else None,
    )
    remediation_planner_payload = read_json(remediation_planner_summary_out)
    remediation_planner_chain_out = _append_remediation_planner_manifest(
        settings.data_dir,
        summary_path=remediation_planner_summary_out,
        planner_status=remediation_planner_payload.get("planner_status") if isinstance(remediation_planner_payload, dict) else None,
        rerun_trend=(
            remediation_planner_payload.get("planner_rerun_diff", {}).get("trend")
            if isinstance(remediation_planner_payload, dict)
            and isinstance(remediation_planner_payload.get("planner_rerun_diff"), dict)
            else None
        ),
        next_best_command=remediation_planner_payload.get("next_best_command") if isinstance(remediation_planner_payload, dict) else None,
        next_feedback_priority_reason=(
            remediation_planner_payload.get("entries", [{}])[0].get("feedback_priority_reason")
            if isinstance(remediation_planner_payload, dict)
            and isinstance(remediation_planner_payload.get("entries"), list)
            and remediation_planner_payload.get("entries")
            else None
        ),
        planned_step_count=remediation_planner_payload.get("planned_step_count") if isinstance(remediation_planner_payload, dict) else None,
    )
    remediation_execution_plan_payload = read_json(remediation_execution_plan_summary_out)
    remediation_execution_plan_chain_out = _append_remediation_execution_plan_manifest(
        settings.data_dir,
        summary_path=remediation_execution_plan_summary_out,
        execution_plan_status=(
            remediation_execution_plan_payload.get("execution_plan_status")
            if isinstance(remediation_execution_plan_payload, dict)
            else None
        ),
        next_action_command=(
            remediation_execution_plan_payload.get("next_action_command")
            if isinstance(remediation_execution_plan_payload, dict)
            else None
        ),
        next_action_feedback_priority_reason=(
            remediation_execution_plan_payload.get("actions", [{}])[0].get("feedback_priority_reason")
            if isinstance(remediation_execution_plan_payload, dict)
            and isinstance(remediation_execution_plan_payload.get("actions"), list)
            and remediation_execution_plan_payload.get("actions")
            else None
        ),
        planned_action_count=(
            remediation_execution_plan_payload.get("planned_action_count")
            if isinstance(remediation_execution_plan_payload, dict)
            else None
        ),
    )
    remediation_session_payload = read_json(remediation_session_summary_out)
    remediation_session_chain_out = _append_remediation_session_manifest(
        settings.data_dir,
        summary_path=remediation_session_summary_out,
        session_status=(
            remediation_session_payload.get("session_status")
            if isinstance(remediation_session_payload, dict)
            else None
        ),
        next_pending_command=(
            remediation_session_payload.get("next_pending_command")
            if isinstance(remediation_session_payload, dict)
            else None
        ),
        next_pending_stage_signal_confidence=(
            remediation_session_payload.get("next_pending_stage_signal_confidence")
            if isinstance(remediation_session_payload, dict)
            else None
        ),
        next_pending_feedback_priority_reason=(
            remediation_session_payload.get("next_pending_feedback_priority_reason")
            if isinstance(remediation_session_payload, dict)
            else None
        ),
        pending_action_count=(
            remediation_session_payload.get("pending_action_count")
            if isinstance(remediation_session_payload, dict)
            else None
        ),
    )
    remediation_session_checkpoint_payload = read_json(remediation_session_checkpoint_summary_out)
    remediation_session_checkpoint_chain_out = _append_remediation_session_checkpoint_manifest(
        settings.data_dir,
        summary_path=remediation_session_checkpoint_summary_out,
        checkpoint_status=(
            remediation_session_checkpoint_payload.get("checkpoint_status")
            if isinstance(remediation_session_checkpoint_payload, dict)
            else None
        ),
        next_action_command=(
            remediation_session_checkpoint_payload.get("next_action_command")
            if isinstance(remediation_session_checkpoint_payload, dict)
            else None
        ),
        next_action_stage_signal_confidence=(
            remediation_session_checkpoint_payload.get("next_action_stage_signal_confidence")
            if isinstance(remediation_session_checkpoint_payload, dict)
            else None
        ),
        next_action_feedback_priority_reason=(
            next(
                (
                    item.get("feedback_priority_reason")
                    for item in remediation_session_checkpoint_payload.get("actions", [])
                    if isinstance(item, dict)
                    and item.get("command") == remediation_session_checkpoint_payload.get("next_action_command")
                ),
                None,
            )
            if isinstance(remediation_session_checkpoint_payload, dict)
            else None
        ),
        pending_action_count=(
            remediation_session_checkpoint_payload.get("pending_action_count")
            if isinstance(remediation_session_checkpoint_payload, dict)
            else None
        ),
    )
    remediation_scoreboard_payload = read_json(remediation_scoreboard_summary_out)
    remediation_scoreboard_chain_out = _append_remediation_scoreboard_manifest(
        settings.data_dir,
        summary_path=remediation_scoreboard_summary_out,
        scoreboard_status=(
            remediation_scoreboard_payload.get("scoreboard_status")
            if isinstance(remediation_scoreboard_payload, dict)
            else None
        ),
        next_action_command=(
            remediation_scoreboard_payload.get("next_action_command")
            if isinstance(remediation_scoreboard_payload, dict)
            else None
        ),
        next_action_stage_signal_confidence=(
            remediation_scoreboard_payload.get("next_action_stage_signal_confidence")
            if isinstance(remediation_scoreboard_payload, dict)
            else None
        ),
        next_action_feedback_priority_reason=(
            next(
                (
                    item.get("feedback_priority_reason")
                    for item in remediation_scoreboard_payload.get("actions", [])
                    if isinstance(item, dict)
                    and item.get("command") == remediation_scoreboard_payload.get("next_action_command")
                ),
                None,
            )
            if isinstance(remediation_scoreboard_payload, dict)
            else None
        ),
        completion_rate=(
            remediation_scoreboard_payload.get("completion_rate")
            if isinstance(remediation_scoreboard_payload, dict)
            else None
        ),
    )
    remediation_evaluator_payload = read_json(remediation_evaluator_summary_out)
    remediation_evaluator_chain_out = _append_remediation_evaluator_manifest(
        settings.data_dir,
        summary_path=remediation_evaluator_summary_out,
        evaluator_status=(
            remediation_evaluator_payload.get("evaluator_status")
            if isinstance(remediation_evaluator_payload, dict)
            else None
        ),
        next_action_key=(
            remediation_evaluator_payload.get("next_action_key")
            if isinstance(remediation_evaluator_payload, dict)
            else None
        ),
        auto_fail_count=(
            remediation_evaluator_payload.get("auto_fail_count")
            if isinstance(remediation_evaluator_payload, dict)
            else None
        ),
    )
    remediation_evidence_payload = read_json(remediation_evidence_summary_out)
    remediation_evidence_chain_out = _append_remediation_evidence_manifest(
        settings.data_dir,
        summary_path=remediation_evidence_summary_out,
        evidence_status=(
            remediation_evidence_payload.get("evidence_status")
            if isinstance(remediation_evidence_payload, dict)
            else None
        ),
        next_manual_review_action_key=(
            remediation_evidence_payload.get("next_manual_review_action_key")
            if isinstance(remediation_evidence_payload, dict)
            else None
        ),
        manual_review_action_count=(
            remediation_evidence_payload.get("manual_review_action_count")
            if isinstance(remediation_evidence_payload, dict)
            else None
        ),
    )
    remediation_command_results_payload = read_json(remediation_command_results_summary_out)
    remediation_command_results_chain_out = _append_remediation_command_results_manifest(
        settings.data_dir,
        summary_path=remediation_command_results_summary_out,
        command_results_status=(
            remediation_command_results_payload.get("command_results_status")
            if isinstance(remediation_command_results_payload, dict)
            else None
        ),
        next_unobserved_action_key=(
            remediation_command_results_payload.get("next_unobserved_action_key")
            if isinstance(remediation_command_results_payload, dict)
            else None
        ),
        missing_observation_count=(
            remediation_command_results_payload.get("missing_observation_count")
            if isinstance(remediation_command_results_payload, dict)
            else None
        ),
    )
    gap_history_out, gap_history_summary_out, _gap_history_text = _write_execution_gap_history(settings.data_dir)
    audit_timeline_out, audit_timeline_summary_out, _audit_timeline_text = _write_audit_timeline(settings.data_dir)
    audit_dashboard_out, audit_dashboard_summary_out, _refreshed_audit_dashboard_text = _write_audit_dashboard(settings.data_dir)
    audit_bundle_out, audit_bundle_manifest_out, _audit_bundle_text = _write_audit_bundle(settings.data_dir)
    audit_bundle_history_out, audit_bundle_history_summary_out, _audit_bundle_history_text = _write_audit_bundle_history(
        settings.data_dir
    )
    current_state_index_out, current_state_index_summary_out, _current_state_index_text = _write_current_state_index(
        settings.data_dir
    )
    readiness_snapshot_out, readiness_snapshot_summary_out, _readiness_snapshot_text = _write_readiness_snapshot(
        settings.data_dir
    )
    logger.info("written: {}", weekly_out)
    logger.info("written: {}", comparison_out)
    logger.info("written: {}", lifecycle_out)
    if daemon_manifest_artifacts is not None:
        logger.info("written: {}", daemon_manifest_artifacts[0])
        logger.info("written: {}", daemon_manifest_artifacts[1])
    if state_export_artifacts is not None:
        logger.info("written: {}", state_export_artifacts[0])
        logger.info("written: {}", state_export_artifacts[1])
    if state_restore_artifacts is not None:
        logger.info("written: {}", state_restore_artifacts[0])
        logger.info("written: {}", state_restore_artifacts[1])
    logger.info("written: {}", execution_snapshot_out)
    logger.info("written: {}", execution_snapshot_summary_out)
    logger.info("written: {}", execution_comparison_out)
    logger.info("written: {}", execution_comparison_summary_out)
    logger.info("written: {}", execution_diagnostics_out)
    logger.info("written: {}", execution_diagnostics_summary_out)
    logger.info("written: {}", execution_read_only_surfaces_out)
    logger.info("written: {}", execution_read_only_surfaces_summary_out)
    logger.info("written: {}", monitoring_out)
    logger.info("written: {}", ops_review_out)
    logger.info("written: {}", ops_review_summary_out)
    logger.info("written: {}", dashboard_out)
    logger.info("written: {}", dashboard_summary_out)
    logger.info("written: {}", runbook_out)
    logger.info("written: {}", runbook_summary_out)
    logger.info("written: {}", cycle_history_out)
    logger.info("written: {}", cycle_history_summary_out)
    logger.info("written: {}", gap_history_out)
    logger.info("written: {}", gap_history_summary_out)
    logger.info("written: {}", state_comparison_out)
    logger.info("written: {}", state_comparison_summary_out)
    logger.info("written: {}", snapshot_drift_out)
    logger.info("written: {}", snapshot_drift_summary_out)
    logger.info("written: {}", drift_overview_out)
    logger.info("written: {}", drift_overview_summary_out)
    logger.info("written: {}", phase_gate_out)
    logger.info("written: {}", phase_gate_summary_out)
    logger.info("written: {}", remediation_planner_out)
    logger.info("written: {}", remediation_planner_summary_out)
    logger.info("written: {}", remediation_execution_plan_out)
    logger.info("written: {}", remediation_execution_plan_summary_out)
    logger.info("written: {}", remediation_session_out)
    logger.info("written: {}", remediation_session_summary_out)
    logger.info("written: {}", remediation_session_checkpoint_out)
    logger.info("written: {}", remediation_session_checkpoint_summary_out)
    logger.info("written: {}", remediation_scoreboard_out)
    logger.info("written: {}", remediation_scoreboard_summary_out)
    logger.info("written: {}", remediation_evaluator_out)
    logger.info("written: {}", remediation_evaluator_summary_out)
    logger.info("written: {}", remediation_evidence_out)
    logger.info("written: {}", remediation_evidence_summary_out)
    logger.info("written: {}", remediation_command_results_out)
    logger.info("written: {}", remediation_command_results_summary_out)
    logger.info("written: {}", bundle_out)
    logger.info("written: {}", bundle_manifest_out)
    logger.info("written: {}", timeline_out)
    logger.info("written: {}", timeline_summary_out)
    logger.info("written: {}", audit_out)
    logger.info("written: {}", audit_manifest_out)
    logger.info("written: {}", audit_timeline_out)
    logger.info("written: {}", audit_timeline_summary_out)
    logger.info("written: {}", audit_dashboard_out)
    logger.info("written: {}", audit_dashboard_summary_out)
    logger.info("written: {}", audit_bundle_out)
    logger.info("written: {}", audit_bundle_manifest_out)
    logger.info("written: {}", audit_bundle_history_out)
    logger.info("written: {}", audit_bundle_history_summary_out)
    logger.info("written: {}", current_state_index_out)
    logger.info("written: {}", current_state_index_summary_out)
    logger.info("written: {}", readiness_snapshot_out)
    logger.info("written: {}", readiness_snapshot_summary_out)
    logger.info("appended: {}", bundle_chain_out)
    logger.info("appended: {}", audit_chain_out)
    logger.info("appended: {}", audit_bundle_chain_out)
    logger.info("appended: {}", remediation_planner_chain_out)
    logger.info("appended: {}", remediation_execution_plan_chain_out)
    logger.info("appended: {}", remediation_session_chain_out)
    logger.info("appended: {}", remediation_session_checkpoint_chain_out)
    logger.info("appended: {}", remediation_scoreboard_chain_out)
    logger.info("appended: {}", remediation_evaluator_chain_out)
    logger.info("appended: {}", remediation_evidence_chain_out)
    logger.info("appended: {}", remediation_command_results_chain_out)
    typer.echo(f"monitoring_status={monitoring['status']}")
    typer.echo(f"execution_snapshot_path={execution_snapshot_out}")
    typer.echo(f"execution_comparison_path={execution_comparison_out}")
    typer.echo(f"execution_diagnostics_path={execution_diagnostics_out}")
    typer.echo(f"execution_read_only_surfaces_path={execution_read_only_surfaces_out}")
    typer.echo(f"execution_gap_history_path={gap_history_out}")
    typer.echo(f"execution_state_comparison_history_path={state_comparison_out}")
    typer.echo(f"execution_snapshot_drift_history_path={snapshot_drift_out}")
    typer.echo(f"execution_drift_overview_path={drift_overview_out}")
    typer.echo(f"dashboard_path={dashboard_out}")
    typer.echo(f"runbook_path={runbook_out}")
    typer.echo(f"phase_gate_review_path={phase_gate_out}")
    typer.echo(f"remediation_planner_path={remediation_planner_out}")
    typer.echo(f"remediation_execution_plan_path={remediation_execution_plan_out}")
    typer.echo(f"remediation_session_path={remediation_session_out}")
    typer.echo(f"remediation_session_checkpoint_path={remediation_session_checkpoint_out}")
    typer.echo(f"remediation_scoreboard_path={remediation_scoreboard_out}")
    typer.echo(f"remediation_evaluator_path={remediation_evaluator_out}")
    typer.echo(f"remediation_evidence_path={remediation_evidence_out}")
    typer.echo(f"remediation_command_results_path={remediation_command_results_out}")
    typer.echo(f"current_state_index_path={current_state_index_out}")
    typer.echo(f"readiness_snapshot_path={readiness_snapshot_out}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")
    typer.echo(dashboard_text)


@app.command("paper-operations-cycle")
def paper_operations_cycle_cmd(
    state_path: Path | None = typer.Option(
        None,
        "--state-path",
        help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
    ),
    signals_path: Path | None = typer.Option(
        None,
        "--signals-path",
        help="Optional signal CSV path. Defaults to data/research/signals.csv.",
    ),
) -> None:
    settings = get_settings()
    summary = _run_paper_step(
        settings.data_dir,
        state_path=state_path,
        signals_path=signals_path,
    )
    execution_lineage = _refresh_execution_lineage_artifacts(settings.data_dir)
    execution_read_only_surfaces_out, execution_read_only_surfaces_summary_out, _execution_read_only_surfaces_text = _write_execution_read_only_surfaces(
        settings.data_dir,
        state_path=state_path,
    )
    execution_snapshot_out, execution_snapshot_summary_out, _execution_snapshot_text = execution_lineage["execution_snapshot"]
    execution_comparison_out, execution_comparison_summary_out, _execution_comparison_text = execution_lineage["execution_comparison"]
    execution_diagnostics_out, execution_diagnostics_summary_out, _execution_diagnostics_text = execution_lineage["execution_diagnostics"]
    weekly_out, _weekly_text = _write_weekly_review(settings.data_dir)
    comparison_out, _comparison_text = _write_comparison_report(settings.data_dir)
    lifecycle_out, _lifecycle_text = _write_lifecycle_report(settings.data_dir)
    monitoring_out, monitoring = _write_monitoring_snapshot(settings.data_dir, state_path)
    ops_review_out, ops_review_summary_out, _ops_review_text = _write_ops_review(settings.data_dir)
    dashboard_out, dashboard_summary_out, dashboard_text = _write_operations_dashboard(settings.data_dir)
    runbook_out, runbook_summary_out, _runbook_text = _write_paper_operations_runbook(settings.data_dir)
    phase_gate_out, phase_gate_summary_out, _phase_gate_text = _write_phase_gate_review(settings.data_dir)
    cycle_summary_path = settings.data_dir / "ops/paper_operations_cycle_summary.json"
    audit_summary = _read_audit_schedule_summary(settings.data_dir)
    phase_gate_summary = _paper_last_run_phase_gate_summary(settings.data_dir)
    execution_summary = _read_execution_schedule_summary(settings.data_dir)
    execution_comparison_summary = _read_execution_comparison_schedule_summary(settings.data_dir)
    execution_diagnostics_summary = _read_execution_diagnostics_schedule_summary(settings.data_dir)
    execution_gap_history_summary = _read_execution_gap_history_schedule_summary(settings.data_dir)
    execution_state_comparison_summary = _read_execution_state_comparison_schedule_summary(
        settings.data_dir
    )
    execution_snapshot_drift_summary = _read_execution_snapshot_drift_schedule_summary(
        settings.data_dir
    )
    execution_drift_overview_summary = _paper_last_run_execution_drift_overview_summary(settings.data_dir)
    readiness_summary = _read_readiness_schedule_summary(settings.data_dir)
    dashboard_summary_payload = read_json(dashboard_summary_out)
    if not isinstance(dashboard_summary_payload, dict):
        dashboard_summary_payload = {}
    latest_execution_lineage = defaulted_all_latest_execution_lineage_fields(
        dashboard_summary_payload
    )
    phase_gate_fields = phase_gate_flat_fields(phase_gate_summary)
    execution_fields = execution_snapshot_flat_fields(execution_summary)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison_summary)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics_summary)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history_summary)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison_summary
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_summary
    )
    readiness_fields = readiness_flat_fields(readiness_summary)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview_summary)
    write_json(
        cycle_summary_path,
        {
            "orders_count": summary.orders_count,
            "fills_count": summary.fills_count,
            "open_positions": summary.open_positions,
            "realized_pnl": summary.realized_pnl,
            "monitoring_status": monitoring["status"],
            "audit": audit_summary,
            "phase_gate": phase_gate_nested_fields(phase_gate_summary),
            **phase_gate_fields,
            "execution_summary": execution_summary,
            **execution_fields,
            "execution_comparison_summary": execution_comparison_summary,
            **execution_comparison_fields,
            "execution_diagnostics_summary": execution_diagnostics_summary,
            **execution_diagnostics_fields,
            "execution_gap_history_summary": execution_gap_history_summary,
            **execution_gap_history_fields,
            "execution_state_comparison_summary": execution_state_comparison_summary,
            **execution_state_comparison_fields,
            "execution_snapshot_drift_summary": execution_snapshot_drift_summary,
            **execution_snapshot_drift_fields,
            "execution_drift_overview_summary": execution_drift_overview_summary,
            **execution_drift_fields,
            "readiness_summary": readiness_summary,
            **readiness_fields,
            **latest_execution_lineage,
            "artifacts": {
                "weekly_review": str(weekly_out),
                "comparison_report": str(comparison_out),
                "lifecycle_report": str(lifecycle_out),
                "execution_snapshot": str(execution_snapshot_out),
                "execution_snapshot_summary": str(execution_snapshot_summary_out),
                "execution_venue_comparison": str(execution_comparison_out),
                "execution_venue_comparison_summary": str(execution_comparison_summary_out),
                "execution_venue_diagnostics": str(execution_diagnostics_out),
                "execution_venue_diagnostics_summary": str(execution_diagnostics_summary_out),
                "execution_gap_history": str(settings.data_dir / "reports/execution_gap_history.md"),
                "execution_gap_history_summary": str(settings.data_dir / "ops/execution_gap_history_summary.json"),
                "execution_state_comparison_history": str(
                    settings.data_dir / "reports/execution_state_comparison_history.md"
                ),
                "execution_state_comparison_history_summary": str(
                    settings.data_dir / "ops/execution_state_comparison_history_summary.json"
                ),
                "execution_snapshot_drift_history": str(
                    settings.data_dir / "reports/execution_snapshot_drift_history.md"
                ),
                "execution_snapshot_drift_history_summary": str(
                    settings.data_dir / "ops/execution_snapshot_drift_history_summary.json"
                ),
                "execution_drift_overview": str(settings.data_dir / "reports/execution_drift_overview.md"),
                "execution_drift_overview_summary": str(
                    settings.data_dir / "ops/execution_drift_overview_summary.json"
                ),
                "monitoring_status": str(monitoring_out),
                "ops_review_report": str(ops_review_out),
                "ops_review_summary": str(ops_review_summary_out),
                "operations_dashboard": str(dashboard_out),
                "operations_dashboard_summary": str(dashboard_summary_out),
                "paper_operations_runbook": str(runbook_out),
                "paper_operations_runbook_summary": str(runbook_summary_out),
                "phase_gate_review": str(phase_gate_out),
                "phase_gate_review_summary": str(phase_gate_summary_out),
                "readiness_snapshot": str(settings.data_dir / "reports/readiness_snapshot.md"),
                "readiness_snapshot_summary": str(settings.data_dir / "ops/readiness_snapshot.json"),
            },
        },
    )
    cycle_manifest_path = _append_paper_operations_cycle_manifest(
        settings.data_dir,
        summary_path=cycle_summary_path,
        monitoring_status=monitoring["status"],
        orders_count=summary.orders_count,
        fills_count=summary.fills_count,
        open_positions=summary.open_positions,
    )
    cycle_history_out, cycle_history_summary_out, _cycle_history_text = _write_paper_cycle_history(settings.data_dir)
    gap_history_out, gap_history_summary_out, _gap_history_text = _write_execution_gap_history(settings.data_dir)
    state_comparison_out, state_comparison_summary_out, _state_comparison_text = _write_execution_state_comparison_history(
        settings.data_dir
    )
    snapshot_drift_out, snapshot_drift_summary_out, _snapshot_drift_text = _write_execution_snapshot_drift_history(
        settings.data_dir
    )
    drift_overview_out, drift_overview_summary_out, _drift_overview_text = _write_execution_drift_overview(
        settings.data_dir
    )
    bundle_out, bundle_manifest_out, _bundle_text = _write_operations_bundle(settings.data_dir)
    timeline_out, timeline_summary_out, _timeline_text = _write_operations_timeline(settings.data_dir)
    audit_out, audit_manifest_out, _audit_text = _write_operations_audit_pack(settings.data_dir)
    audit_timeline_out, audit_timeline_summary_out, _audit_timeline_text = _write_audit_timeline(settings.data_dir)
    audit_dashboard_out, audit_dashboard_summary_out, _audit_dashboard_text = _write_audit_dashboard(settings.data_dir)
    audit_bundle_out, audit_bundle_manifest_out, _audit_bundle_text = _write_audit_bundle(settings.data_dir)
    bundle_payload = read_json(bundle_manifest_out)
    bundle_chain_out = _append_operations_snapshot_manifest(
        settings.data_dir,
        manifest_path=bundle_manifest_out,
        overall_status=bundle_payload.get("overall_status") if isinstance(bundle_payload, dict) else None,
        cycle_count=bundle_payload.get("cycle_count") if isinstance(bundle_payload, dict) else None,
    )
    audit_payload = read_json(audit_manifest_out)
    audit_chain_out = _append_operations_audit_snapshot_manifest(
        settings.data_dir,
        manifest_path=audit_manifest_out,
        overall_status=audit_payload.get("overall_status") if isinstance(audit_payload, dict) else None,
        timeline_latest_operation=audit_payload.get("timeline_latest_operation") if isinstance(audit_payload, dict) else None,
    )
    audit_bundle_payload = read_json(audit_bundle_manifest_out)
    audit_bundle_chain_out = _append_audit_bundle_snapshot_manifest(
        settings.data_dir,
        manifest_path=audit_bundle_manifest_out,
        overall_status=audit_bundle_payload.get("overall_status") if isinstance(audit_bundle_payload, dict) else None,
        timeline_latest_operation=audit_bundle_payload.get("timeline_latest_operation") if isinstance(audit_bundle_payload, dict) else None,
    )
    gap_history_out, gap_history_summary_out, _gap_history_text = _write_execution_gap_history(settings.data_dir)
    audit_timeline_out, audit_timeline_summary_out, _audit_timeline_text = _write_audit_timeline(settings.data_dir)
    audit_dashboard_out, audit_dashboard_summary_out, _refreshed_audit_dashboard_text = _write_audit_dashboard(settings.data_dir)
    audit_bundle_out, audit_bundle_manifest_out, _audit_bundle_text = _write_audit_bundle(settings.data_dir)
    audit_bundle_history_out, audit_bundle_history_summary_out, _audit_bundle_history_text = _write_audit_bundle_history(
        settings.data_dir
    )
    current_state_index_out, current_state_index_summary_out, _current_state_index_text = _write_current_state_index(
        settings.data_dir
    )
    readiness_snapshot_out, readiness_snapshot_summary_out, _readiness_snapshot_text = _write_readiness_snapshot(
        settings.data_dir
    )
    logger.info("written: {}", summary.orders_path)
    logger.info("written: {}", summary.fills_path)
    logger.info("written: {}", summary.positions_path)
    logger.info("written: {}", summary.daily_pnl_path)
    logger.info("written: {}", summary.report_path)
    logger.info("written: {}", execution_snapshot_out)
    logger.info("written: {}", execution_snapshot_summary_out)
    logger.info("written: {}", execution_comparison_out)
    logger.info("written: {}", execution_comparison_summary_out)
    logger.info("written: {}", execution_diagnostics_out)
    logger.info("written: {}", execution_diagnostics_summary_out)
    logger.info("written: {}", execution_read_only_surfaces_out)
    logger.info("written: {}", execution_read_only_surfaces_summary_out)
    logger.info("written: {}", weekly_out)
    logger.info("written: {}", comparison_out)
    logger.info("written: {}", lifecycle_out)
    logger.info("written: {}", monitoring_out)
    logger.info("written: {}", ops_review_out)
    logger.info("written: {}", ops_review_summary_out)
    logger.info("written: {}", dashboard_out)
    logger.info("written: {}", dashboard_summary_out)
    logger.info("written: {}", runbook_out)
    logger.info("written: {}", runbook_summary_out)
    logger.info("written: {}", phase_gate_out)
    logger.info("written: {}", phase_gate_summary_out)
    logger.info("written: {}", cycle_history_out)
    logger.info("written: {}", cycle_history_summary_out)
    logger.info("written: {}", gap_history_out)
    logger.info("written: {}", gap_history_summary_out)
    logger.info("written: {}", state_comparison_out)
    logger.info("written: {}", state_comparison_summary_out)
    logger.info("written: {}", snapshot_drift_out)
    logger.info("written: {}", snapshot_drift_summary_out)
    logger.info("written: {}", drift_overview_out)
    logger.info("written: {}", drift_overview_summary_out)
    logger.info("written: {}", bundle_out)
    logger.info("written: {}", bundle_manifest_out)
    logger.info("written: {}", timeline_out)
    logger.info("written: {}", timeline_summary_out)
    logger.info("written: {}", audit_out)
    logger.info("written: {}", audit_manifest_out)
    logger.info("written: {}", audit_timeline_out)
    logger.info("written: {}", audit_timeline_summary_out)
    logger.info("written: {}", audit_dashboard_out)
    logger.info("written: {}", audit_dashboard_summary_out)
    logger.info("written: {}", audit_bundle_out)
    logger.info("written: {}", audit_bundle_manifest_out)
    logger.info("written: {}", audit_bundle_history_out)
    logger.info("written: {}", audit_bundle_history_summary_out)
    logger.info("written: {}", current_state_index_out)
    logger.info("written: {}", current_state_index_summary_out)
    logger.info("written: {}", readiness_snapshot_out)
    logger.info("written: {}", readiness_snapshot_summary_out)
    logger.info("appended: {}", bundle_chain_out)
    logger.info("appended: {}", audit_chain_out)
    logger.info("appended: {}", audit_bundle_chain_out)
    logger.info("written: {}", cycle_summary_path)
    logger.info("appended: {}", cycle_manifest_path)
    typer.echo(f"orders={summary.orders_count}")
    typer.echo(f"fills={summary.fills_count}")
    typer.echo(f"open_positions={summary.open_positions}")
    typer.echo(f"realized_pnl={summary.realized_pnl}")
    typer.echo(f"monitoring_status={monitoring['status']}")
    typer.echo(f"execution_snapshot_path={execution_snapshot_out}")
    typer.echo(f"execution_comparison_path={execution_comparison_out}")
    typer.echo(f"execution_diagnostics_path={execution_diagnostics_out}")
    typer.echo(f"execution_read_only_surfaces_path={execution_read_only_surfaces_out}")
    typer.echo(f"execution_gap_history_path={gap_history_out}")
    typer.echo(f"execution_state_comparison_history_path={state_comparison_out}")
    typer.echo(f"execution_snapshot_drift_history_path={snapshot_drift_out}")
    typer.echo(f"execution_drift_overview_path={drift_overview_out}")
    typer.echo(f"cycle_summary_path={cycle_summary_path}")
    typer.echo(f"cycle_manifest_path={cycle_manifest_path}")
    typer.echo(f"phase_gate_review_path={phase_gate_out}")
    typer.echo(f"current_state_index_path={current_state_index_out}")
    typer.echo(f"readiness_snapshot_path={readiness_snapshot_out}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")
    typer.echo(dashboard_text)


@app.command("build-backtest")
def build_backtest(
    signals_path: Path | None = typer.Option(
        None,
        "--signals-path",
        help="Optional research signal CSV. Defaults to data/research/signals.csv when present.",
    )
) -> None:
    settings = get_settings()
    latest_execution_payload = _paper_last_run_latest_execution_payload(settings.data_dir)
    default_signals_path = settings.data_dir / "research/signals.csv"
    selected_signals_path = signals_path or default_signals_path
    if signals_path is not None and not selected_signals_path.exists():
        typer.echo(f"Research signal CSV not found: {selected_signals_path}")
        raise typer.Exit(code=2)
    decision_log_path = (
        settings.data_dir / "evidence/decision_logs" / f"backtest_decisions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
    )
    decision_summary_path = settings.data_dir / "research/decision_summary.json"
    metrics, _records, _summary = run_backtest_bridge_with_decisions(
        settings.data_dir / "normalized/quotes.parquet",
        selected_signals_path if selected_signals_path.exists() else None,
        settings.data_dir / "research/venue_cost_matrix.csv",
        decision_log_path=decision_log_path,
        decision_summary_path=decision_summary_path,
        audit_summary=_paper_last_run_audit_summary(settings.data_dir),
        phase_gate_summary=_paper_last_run_phase_gate_summary(settings.data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings.data_dir),
        execution_summary=_read_execution_schedule_summary(settings.data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings.data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings.data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(settings.data_dir),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings.data_dir),
        **latest_execution_payload,
    )
    report_path = settings.data_dir / "research/backtest_report.md"
    metrics_path = settings.data_dir / "research/backtest_metrics.json"
    metrics_summary_path = settings.data_dir / "research/backtest_metrics_summary.json"
    write_backtest_report(
        metrics,
        report_path,
        selected_signals_path if selected_signals_path.exists() else None,
        audit_summary=_paper_last_run_audit_summary(settings.data_dir),
        phase_gate_summary=_paper_last_run_phase_gate_summary(settings.data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings.data_dir),
        execution_summary=_read_execution_schedule_summary(settings.data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings.data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings.data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
            settings.data_dir
        ),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings.data_dir),
        **latest_execution_payload,
    )
    write_backtest_metrics_json(metrics, metrics_path)
    write_backtest_metrics_summary_json(
        metrics,
        metrics_summary_path,
        audit_summary=_paper_last_run_audit_summary(settings.data_dir),
        phase_gate_summary=_paper_last_run_phase_gate_summary(settings.data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings.data_dir),
        execution_summary=_read_execution_schedule_summary(settings.data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings.data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings.data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(settings.data_dir),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings.data_dir),
        **latest_execution_payload,
    )
    logger.info("written: {}", report_path)
    logger.info("written: {}", metrics_path)
    logger.info("written: {}", metrics_summary_path)
    logger.info("written: {}", decision_log_path)
    logger.info("written: {}", decision_summary_path)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("check-halt-policy")
def check_halt_policy() -> None:
    settings = get_settings()
    policy = load_halt_policy()
    for line in summarize_halt_policy(policy):
        typer.echo(line)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("check-go-no-go")
def check_go_no_go() -> None:
    settings = get_settings()
    latest_execution_payload = _paper_last_run_latest_execution_payload(settings.data_dir)
    report = build_go_no_go_report(settings.data_dir)
    out = settings.data_dir / "research/go_no_go_report.md"
    write_go_no_go_markdown(
        report,
        out,
        audit_summary=_paper_last_run_audit_summary(settings.data_dir),
        phase_gate_summary=_paper_last_run_phase_gate_summary(settings.data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings.data_dir),
        execution_summary=_read_execution_schedule_summary(settings.data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings.data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings.data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
            settings.data_dir
        ),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings.data_dir),
        **latest_execution_payload,
    )
    logger.info("written: {}", out)
    typer.echo(report.decision.value)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("build-evidence-card")
def build_evidence_card_cmd() -> None:
    settings = get_settings()
    latest_execution_payload = _paper_last_run_latest_execution_payload(settings.data_dir)
    out = build_evidence_card(
        settings.data_dir,
        settings.data_dir / "evidence",
        audit_summary=_paper_last_run_audit_summary(settings.data_dir),
        phase_gate_summary=_paper_last_run_phase_gate_summary(settings.data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings.data_dir),
        **latest_execution_payload,
        execution_summary=_read_execution_schedule_summary(settings.data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings.data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings.data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(settings.data_dir),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings.data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings.data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings.data_dir),
    )
    logger.info("written: {}", out)
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("implementation-status")
def implementation_status(write: bool = typer.Option(False, "--write")) -> None:
    settings = get_settings()
    if write:
        out = Path("docs/IMPLEMENTATION_STATUS.md")
        write_implementation_status(out)
        logger.info("written: {}", out)
    for item in implementation_status_items():
        typer.echo(f"{item.status}\t{item.area}\t{item.item}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("check-timeframe")
def check_timeframe_cmd(timeframe: str) -> None:
    settings = get_settings()
    decision = check_timeframe(timeframe)
    if decision.allowed:
        typer.echo(f"ALLOW: {timeframe}")
        for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
        return
    typer.echo(f"BLOCK: {timeframe} reason={decision.reason}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")
    raise typer.Exit(code=2)


@app.command("market-session")
def market_session(venue: str = typer.Option(..., "--venue"), symbol: str = typer.Option(..., "--symbol")) -> None:
    settings = get_settings()
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
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("next-live-window")
def next_live_window(venue: str = typer.Option(..., "--venue"), symbol: str = typer.Option(..., "--symbol")) -> None:
    settings = get_settings()
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
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


@app.command("validate-artifacts")
def validate_artifacts_cmd(strict: bool = typer.Option(False, "--strict")) -> None:
    settings = get_settings()
    summary = validate_artifacts(settings.data_dir, Path("schemas"), strict=strict)
    typer.echo(f"checked_files={summary.checked_files}")
    typer.echo(f"issues={len(summary.issues)}")
    for issue in summary.issues:
        typer.echo(f"{issue.path}: {issue.message}")
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")
    if summary.issues:
        raise typer.Exit(code=2)


@app.command("diagnose-quotes")
def diagnose_quotes(
    venue: str | None = typer.Option(None, "--venue"),
    symbol: str | None = typer.Option(None, "--symbol"),
) -> None:
    settings = get_settings()
    try:
        policy = load_halt_policy()
        stale_policy = policy.get("halt_policy", policy).get("stale_price", {})
    except FileNotFoundError:
        stale_policy = {}
    stale_thresholds = {
        "gtrade": int(stale_policy.get("gtrade_max_age_ms", 3000)),
        "ostium": int(stale_policy.get("ostium_max_age_ms", 5000)),
    }
    diagnostics = build_quote_diagnostics(
        settings.data_dir / "raw/quotes",
        venue=venue,
        symbol=symbol,
        stale_thresholds_ms=stale_thresholds,
    )
    if not diagnostics:
        typer.echo("No quote rows found for diagnostics.")
        raise typer.Exit(code=2)
    for item in diagnostics:
        typer.echo(f"venue={item.venue} symbol={item.symbol}")
        typer.echo(f"stale_threshold_ms={item.stale_threshold_ms}")
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
    build_quote_diagnostics_report(
        raw_quotes_root=settings.data_dir / "raw/quotes",
        venue=venue,
        symbol=symbol,
        stale_thresholds_ms=stale_thresholds,
        out_path=settings.data_dir / "reports/quote_diagnostics.md",
        summary_path=settings.data_dir / "ops/quote_diagnostics_summary.json",
    )
    for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
        typer.echo(f"recommended_read_order_{index}={item}")


def main() -> None:
    app()
