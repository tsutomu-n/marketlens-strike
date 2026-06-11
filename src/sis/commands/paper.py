from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

import polars as pl
import typer
from loguru import logger

from sis.paper.fills import PaperFill
from sis.paper.portfolio import PaperPosition
from sis.paper.report import build_daily_paper_report
from sis.paper.runner import run_paper_from_intents
from sis.settings import get_settings
from sis.state.store import StateStore


def register_paper_commands(
    app: typer.Typer,
    *,
    _run_paper_step: Callable[..., Any],
    _read_audit_schedule_summary: Callable[..., Any],
    _paper_last_run_latest_execution_payload: Callable[..., Any],
    _paper_last_run_phase_gate_summary: Callable[..., Any],
    _paper_last_run_readiness_summary: Callable[..., Any],
    _paper_last_run_execution_gap_history_summary: Callable[..., Any],
    _paper_last_run_execution_state_comparison_summary: Callable[..., Any],
    _paper_last_run_execution_snapshot_drift_summary: Callable[..., Any],
    _paper_last_run_execution_drift_overview_summary: Callable[..., Any],
    _write_weekly_review: Callable[..., Any],
    _recommended_read_order: Callable[..., Any],
) -> None:
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

    @app.command("paper-from-intents")
    def paper_from_intents_cmd(
        intents_path: Path = typer.Option(
            Path("data/bot/paper_intent_preview.json"),
            "--intents-path",
            help="PaperIntentPreview JSON path.",
        ),
        state_path: Path | None = typer.Option(
            None,
            "--state-path",
            help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
        ),
        observation_ledger_path: Path | None = typer.Option(
            None,
            "--observation-ledger-path",
            dir_okay=False,
            help=(
                "Optional paper observation ledger path. "
                "Defaults to data/paper/paper_observation_ledger.jsonl."
            ),
        ),
    ) -> None:
        settings = get_settings()
        summary = run_paper_from_intents(
            settings.data_dir,
            intents_path=intents_path,
            state_path=state_path,
            observation_ledger_path=observation_ledger_path,
        )
        logger.info("written: {}", summary.orders_path)
        logger.info("written: {}", summary.fills_path)
        logger.info("written: {}", summary.positions_path)
        logger.info("written: {}", summary.observation_ledger_path)
        typer.echo(f"orders={summary.orders_count}")
        typer.echo(f"fills={summary.fills_count}")
        typer.echo(f"blocked={summary.blocked_count}")
        typer.echo(f"observation_ledger_path={summary.observation_ledger_path}")
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
        positions_frame = (
            pl.read_parquet(positions_path) if positions_path.exists() else pl.DataFrame()
        )
        fills = fills_frame.to_dicts()
        positions = positions_frame.to_dicts()
        paper_last_run = StateStore(settings.data_dir / "state/marketlens.sqlite").get_json(
            "paper_last_run"
        )
        audit_summary = (
            cast(dict[str, object], paper_last_run).get("audit")
            if isinstance(paper_last_run, dict)
            else None
        )
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
            execution_drift_overview_summary=_paper_last_run_execution_drift_overview_summary(
                settings.data_dir
            ),
        )
        logger.info("written: {}", out)
        typer.echo(text)
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
