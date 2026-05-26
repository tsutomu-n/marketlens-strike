from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

import typer
from loguru import logger

from sis.settings import get_settings
from sis.storage.jsonl_store import read_json


class _SimpleReportWriter(Protocol):
    def __call__(self, settings_data_dir: Path) -> tuple[Path, str]: ...


class _SummaryReportWriter(Protocol):
    def __call__(self, settings_data_dir: Path) -> tuple[Path, Path, str]: ...


def register_operations_report_commands(
    app: typer.Typer,
    *,
    write_lifecycle_report_fn: _SimpleReportWriter,
    write_comparison_report_fn: _SimpleReportWriter,
    write_ops_review_fn: _SummaryReportWriter,
    write_operations_dashboard_fn: _SummaryReportWriter,
    write_paper_operations_runbook_fn: _SummaryReportWriter,
    write_paper_cycle_history_fn: _SummaryReportWriter,
    write_execution_gap_history_fn: _SummaryReportWriter,
    write_execution_state_comparison_history_fn: _SummaryReportWriter,
    write_execution_snapshot_drift_history_fn: _SummaryReportWriter,
    write_execution_drift_overview_fn: _SummaryReportWriter,
    write_phase_gate_review_fn: _SummaryReportWriter,
    write_operations_bundle_fn: _SummaryReportWriter,
    write_operations_timeline_fn: _SummaryReportWriter,
    write_operations_audit_pack_fn: _SummaryReportWriter,
    write_audit_timeline_fn: _SummaryReportWriter,
    write_audit_dashboard_fn: _SummaryReportWriter,
    write_audit_bundle_fn: _SummaryReportWriter,
    write_audit_bundle_history_fn: _SummaryReportWriter,
    write_current_state_index_fn: _SummaryReportWriter,
    write_readiness_snapshot_fn: _SummaryReportWriter,
    append_operations_snapshot_manifest_fn: Callable[..., Path],
    append_operations_audit_snapshot_manifest_fn: Callable[..., Path],
    append_audit_bundle_snapshot_manifest_fn: Callable[..., Path],
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
        @app.command("lifecycle-report")
        def lifecycle_report_cmd() -> None:
            settings = get_settings()
            out, text = write_lifecycle_report_fn(settings.data_dir)
            logger.info("written: {}", out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("comparison-report")
        def comparison_report_cmd() -> None:
            settings = get_settings()
            out, text = write_comparison_report_fn(settings.data_dir)
            logger.info("written: {}", out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("ops-review")
        def ops_review_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_ops_review_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("operations-dashboard")
        def operations_dashboard_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_operations_dashboard_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("paper-operations-runbook")
        def paper_operations_runbook_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_paper_operations_runbook_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("paper-cycle-history")
        def paper_cycle_history_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_paper_cycle_history_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("execution-gap-history")
        def execution_gap_history_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_execution_gap_history_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("execution-state-comparison-history")
        def execution_state_comparison_history_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_execution_state_comparison_history_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("execution-snapshot-drift-history")
        def execution_snapshot_drift_history_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_execution_snapshot_drift_history_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("execution-drift-overview")
        def execution_drift_overview_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_execution_drift_overview_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("phase-gate-review")
        def phase_gate_review_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_phase_gate_review_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("operations-bundle")
        def operations_bundle_cmd() -> None:
            settings = get_settings()
            out, manifest_out, text = write_operations_bundle_fn(settings.data_dir)
            payload = read_json(manifest_out)
            chain_out = append_operations_snapshot_manifest_fn(
                settings.data_dir,
                manifest_path=manifest_out,
                overall_status=payload.get("overall_status") if isinstance(payload, dict) else None,
                cycle_count=payload.get("cycle_count") if isinstance(payload, dict) else None,
            )
            logger.info("written: {}", out)
            logger.info("written: {}", manifest_out)
            logger.info("appended: {}", chain_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("operations-timeline")
        def operations_timeline_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_operations_timeline_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("operations-audit-pack")
        def operations_audit_pack_cmd() -> None:
            settings = get_settings()
            out, manifest_out, text = write_operations_audit_pack_fn(settings.data_dir)
            payload = read_json(manifest_out)
            chain_out = append_operations_audit_snapshot_manifest_fn(
                settings.data_dir,
                manifest_path=manifest_out,
                overall_status=payload.get("overall_status") if isinstance(payload, dict) else None,
                timeline_latest_operation=payload.get("timeline_latest_operation") if isinstance(payload, dict) else None,
            )
            logger.info("written: {}", out)
            logger.info("written: {}", manifest_out)
            logger.info("appended: {}", chain_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("audit-timeline")
        def audit_timeline_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_audit_timeline_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("audit-dashboard")
        def audit_dashboard_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_audit_dashboard_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("audit-bundle")
        def audit_bundle_cmd() -> None:
            settings = get_settings()
            out, manifest_out, text = write_audit_bundle_fn(settings.data_dir)
            payload = read_json(manifest_out)
            chain_out = append_audit_bundle_snapshot_manifest_fn(
                settings.data_dir,
                manifest_path=manifest_out,
                overall_status=payload.get("overall_status") if isinstance(payload, dict) else None,
                timeline_latest_operation=payload.get("timeline_latest_operation") if isinstance(payload, dict) else None,
            )
            audit_timeline_out, audit_timeline_summary_out, _ = write_audit_timeline_fn(settings.data_dir)
            audit_dashboard_out, audit_dashboard_summary_out, _ = write_audit_dashboard_fn(settings.data_dir)
            out, manifest_out, text = write_audit_bundle_fn(settings.data_dir)
            audit_bundle_history_out, audit_bundle_history_summary_out, _ = write_audit_bundle_history_fn(settings.data_dir)
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
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("audit-bundle-history")
        def audit_bundle_history_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_audit_bundle_history_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("current-state-index")
        def current_state_index_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_current_state_index_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
    
        @app.command("readiness-snapshot")
        def readiness_snapshot_cmd() -> None:
            settings = get_settings()
            out, summary_out, text = write_readiness_snapshot_fn(settings.data_dir)
            logger.info("written: {}", out)
            logger.info("written: {}", summary_out)
            typer.echo(text)
            for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
                typer.echo(f"recommended_read_order_{index}={item}")
