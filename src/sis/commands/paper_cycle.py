from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import typer
from loguru import logger

from sis.settings import get_settings
from sis.storage.jsonl_store import read_json
from sis.reports.summary_normalizers import (
    defaulted_all_latest_execution_lineage_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    phase_gate_flat_fields,
    phase_gate_nested_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import write_json



def register_paper_cycle_commands(
    app: typer.Typer,
    *,
    _run_paper_step: Callable[..., Any],
    _refresh_execution_lineage_artifacts: Callable[..., Any],
    _write_execution_read_only_surfaces: Callable[..., Any],
    _write_weekly_review: Callable[..., Any],
    _write_comparison_report: Callable[..., Any],
    _write_lifecycle_report: Callable[..., Any],
    _write_monitoring_snapshot: Callable[..., Any],
    _write_ops_review: Callable[..., Any],
    _write_operations_dashboard: Callable[..., Any],
    _write_paper_operations_runbook: Callable[..., Any],
    _write_phase_gate_review: Callable[..., Any],
    _read_audit_schedule_summary: Callable[..., Any],
    _paper_last_run_phase_gate_summary: Callable[..., Any],
    _read_execution_schedule_summary: Callable[..., Any],
    _read_execution_comparison_schedule_summary: Callable[..., Any],
    _read_execution_diagnostics_schedule_summary: Callable[..., Any],
    _read_execution_gap_history_schedule_summary: Callable[..., Any],
    _read_execution_state_comparison_schedule_summary: Callable[..., Any],
    _read_execution_snapshot_drift_schedule_summary: Callable[..., Any],
    _paper_last_run_execution_drift_overview_summary: Callable[..., Any],
    _read_readiness_schedule_summary: Callable[..., Any],
    _append_paper_operations_cycle_manifest: Callable[..., Any],
    _write_paper_cycle_history: Callable[..., Any],
    _write_execution_gap_history: Callable[..., Any],
    _write_execution_state_comparison_history: Callable[..., Any],
    _write_execution_snapshot_drift_history: Callable[..., Any],
    _write_execution_drift_overview: Callable[..., Any],
    _write_operations_bundle: Callable[..., Any],
    _write_operations_timeline: Callable[..., Any],
    _write_operations_audit_pack: Callable[..., Any],
    _write_audit_timeline: Callable[..., Any],
    _write_audit_dashboard: Callable[..., Any],
    _write_audit_bundle: Callable[..., Any],
    _append_operations_snapshot_manifest: Callable[..., Any],
    _append_operations_audit_snapshot_manifest: Callable[..., Any],
    _append_audit_bundle_snapshot_manifest: Callable[..., Any],
    _write_audit_bundle_history: Callable[..., Any],
    _write_current_state_index: Callable[..., Any],
    _write_readiness_snapshot: Callable[..., Any],
    _recommended_read_order: Callable[..., Any],
) -> None:
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
