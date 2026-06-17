from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import typer
from loguru import logger

from sis.backtest.bridge import (
    run_backtest_bridge_with_decisions,
    write_backtest_metrics_json,
    write_backtest_metrics_summary_json,
    write_backtest_report,
)
from sis.market_calendar import market_session_window
from sis.reports.doc_paths import CODE_STATUS_DOC
from sis.reports.evidence import build_evidence_card
from sis.reports.go_no_go import build_go_no_go_report, write_go_no_go_markdown
from sis.reports.implementation_status import (
    implementation_status_items,
    write_implementation_status,
)
from sis.reports.quote_diagnostics import build_quote_diagnostics, build_quote_diagnostics_report
from sis.risk.halt_policy import load_halt_policy, summarize_halt_policy
from sis.risk.scalping_policy import check_timeframe
from sis.settings import get_settings
from sis.validation.artifacts import validate_artifacts


def register_review_commands(
    app: typer.Typer,
    *,
    _paper_last_run_latest_execution_payload: Callable[..., Any],
    _paper_last_run_audit_summary: Callable[..., Any],
    _paper_last_run_phase_gate_summary: Callable[..., Any],
    _read_readiness_schedule_summary: Callable[..., Any],
    _read_execution_schedule_summary: Callable[..., Any],
    _read_execution_comparison_schedule_summary: Callable[..., Any],
    _read_execution_diagnostics_schedule_summary: Callable[..., Any],
    _read_execution_gap_history_schedule_summary: Callable[..., Any],
    _read_execution_state_comparison_schedule_summary: Callable[..., Any],
    _read_execution_snapshot_drift_schedule_summary: Callable[..., Any],
    _read_execution_drift_overview_schedule_summary: Callable[..., Any],
    _recommended_read_order: Callable[..., Any],
) -> None:
    @app.command("build-backtest")
    def build_backtest(
        signals_path: Path | None = typer.Option(
            None,
            "--signals-path",
            help="Optional research signal CSV. Defaults to data/research/signals.csv when present.",
        ),
    ) -> None:
        settings = get_settings()
        latest_execution_payload = _paper_last_run_latest_execution_payload(settings.data_dir)
        default_signals_path = settings.data_dir / "research/signals.csv"
        selected_signals_path = signals_path or default_signals_path
        if signals_path is not None and not selected_signals_path.exists():
            typer.echo(f"Research signal CSV not found: {selected_signals_path}")
            raise typer.Exit(code=2)
        decision_log_path = (
            settings.data_dir
            / "evidence/decision_logs"
            / f"backtest_decisions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
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
            execution_comparison_summary=_read_execution_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(
                settings.data_dir
            ),
            execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
                settings.data_dir
            ),
            execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
                settings.data_dir
            ),
            execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(
                settings.data_dir
            ),
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
            execution_comparison_summary=_read_execution_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(
                settings.data_dir
            ),
            execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
                settings.data_dir
            ),
            execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
                settings.data_dir
            ),
            execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(
                settings.data_dir
            ),
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
            execution_comparison_summary=_read_execution_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(
                settings.data_dir
            ),
            execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
                settings.data_dir
            ),
            execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
                settings.data_dir
            ),
            execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(
                settings.data_dir
            ),
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
            execution_comparison_summary=_read_execution_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(
                settings.data_dir
            ),
            execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
                settings.data_dir
            ),
            execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
                settings.data_dir
            ),
            execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(
                settings.data_dir
            ),
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
            execution_comparison_summary=_read_execution_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(
                settings.data_dir
            ),
            execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
                settings.data_dir
            ),
            execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
                settings.data_dir
            ),
            execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
                settings.data_dir
            ),
            execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(
                settings.data_dir
            ),
        )
        logger.info("written: {}", out)
        for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("implementation-status")
    def implementation_status(write: bool = typer.Option(False, "--write")) -> None:
        settings = get_settings()
        if write:
            out = Path(CODE_STATUS_DOC)
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
    def market_session(
        venue: str = typer.Option(..., "--venue"), symbol: str = typer.Option(..., "--symbol")
    ) -> None:
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
    def next_live_window(
        venue: str = typer.Option(..., "--venue"), symbol: str = typer.Option(..., "--symbol")
    ) -> None:
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
        venue: str | None = typer.Option(None, "--venue", help="Optional venue filter."),
        symbol: str | None = typer.Option(
            None, "--symbol", help="Optional canonical symbol filter."
        ),
    ) -> None:
        """Diagnose local quote rows and write operator reports.

        Reads JSONL files under data/raw/quotes, applies optional venue/symbol
        filters, and prints per-symbol stale/tradable/missing-field rates. Writes
        data/reports/quote_diagnostics.md and
        data/ops/quote_diagnostics_summary.json. For --venue trade_xyz, only the
        latest venue file is diagnosed. Performs no external API calls and
        submits no orders.
        """
        settings = get_settings()
        try:
            policy = load_halt_policy()
            stale_policy = policy.get("halt_policy", policy).get("stale_price", {})
        except FileNotFoundError:
            stale_policy = {}
        stale_thresholds = {
            "gtrade": int(stale_policy.get("gtrade_max_age_ms", 3000)),
            "ostium": int(stale_policy.get("ostium_max_age_ms", 5000)),
            "trade_xyz": int(stale_policy.get("trade_xyz_max_age_ms", 5000)),
        }
        diagnostics = build_quote_diagnostics(
            settings.data_dir / "raw/quotes",
            venue=venue,
            symbol=symbol,
            stale_thresholds_ms=stale_thresholds,
            latest_only=venue == "trade_xyz",
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
            typer.echo(f"missing_oracle_price_rate={item.missing_oracle_price_rate:.4f}")
            typer.echo(f"missing_funding_rate={item.missing_funding_rate:.4f}")
            typer.echo(f"missing_open_interest_rate={item.missing_open_interest_rate:.4f}")
            typer.echo(f"missing_spread_rate={item.missing_spread_rate:.4f}")
            typer.echo(f"l2_only_rate={item.l2_only_rate:.4f}")
            typer.echo(f"fee_mode_unknown_rate={item.fee_mode_unknown_rate:.4f}")
            typer.echo(f"block_reason_distribution={item.block_reason_distribution}")
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
            latest_only=venue == "trade_xyz",
            out_path=settings.data_dir / "reports/quote_diagnostics.md",
            summary_path=settings.data_dir / "ops/quote_diagnostics_summary.json",
        )
        for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
