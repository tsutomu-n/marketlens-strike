from __future__ import annotations

import shlex
from pathlib import Path
from typing import Callable, Protocol

import typer
from loguru import logger

from sis.ops.alerts import queue_notification, write_alert
from sis.ops.daemon import create_daemon_manifest, run_daemon_dry_run, run_daemon_loop, write_daemon_manifest
from sis.ops.daily_loss_limit import evaluate_daily_loss_limit, evaluate_max_exposure
from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.reports.ops_command_status import (
    build_alert_report,
    build_healthcheck_report,
    build_kill_switch_report,
    build_notification_outbox_report,
    build_schedule_run_report,
)
from sis.reports.state_command_status import build_daemon_loop_report
from sis.settings import get_settings
from sis.storage.jsonl_store import read_json
from sis.state.recovery import export_state_snapshot, restore_state_snapshot
from sis.state.store import StateStore


class _StateStoreFactory(Protocol):
    def __call__(self, settings_data_dir: Path, state_path: Path | None) -> StateStore: ...


class _MonitoringSnapshotWriter(Protocol):
    def __call__(self, settings_data_dir: Path, state_path: Path | None) -> tuple[Path, dict]: ...


class _ScheduleRunRecord(Protocol):
    run_type: str
    scheduled_for: object


class _ScheduleRunWriter(Protocol):
    def __call__(
        self,
        settings_data_dir: Path,
        *,
        run_type: str,
        command: str,
        at: str | None,
        every_minutes: int | None,
    ) -> tuple[_ScheduleRunRecord, Path]: ...


class _OperationManifestBuilder(Protocol):
    def __call__(
        self,
        *,
        operation: str,
        mode: str,
        command: str,
        status: str,
        artifacts: list[str],
        notes: list[str],
    ) -> dict: ...


class _OperationManifestAppender(Protocol):
    def __call__(self, chain_path: Path, manifest: dict) -> Path: ...


class _ExecutionLineageRefresher(Protocol):
    def __call__(self, settings_data_dir: Path, *, only_if_sources_exist: bool = False) -> None: ...


class _ExecutionReadOnlyWriter(Protocol):
    def __call__(
        self,
        settings_data_dir: Path,
        *,
        state_path: Path | None = None,
    ) -> tuple[Path, Path, str]: ...


class _DaemonDryRunContextBuilder(Protocol):
    def __call__(self, settings_data_dir: Path) -> dict: ...


class _DaemonManifestArtifactsWriter(Protocol):
    def __call__(self, settings_data_dir: Path) -> tuple[Path, Path, str] | None: ...


class _StateArtifactsWriter(Protocol):
    def __call__(self, settings_data_dir: Path, *, state_store_path: Path | None = None) -> tuple[Path, Path, str] | None: ...


class _StateRestoreArtifactsWriter(Protocol):
    def __call__(
        self,
        settings_data_dir: Path,
        *,
        snapshot_path: Path,
        state_store_path: Path | None = None,
        restored: bool = True,
    ) -> tuple[Path, Path, str] | None: ...


class _SimpleReportWriter(Protocol):
    def __call__(self, settings_data_dir: Path) -> tuple[Path, str]: ...


class _SummaryReportWriter(Protocol):
    def __call__(self, settings_data_dir: Path) -> tuple[Path, Path, str]: ...


def register_ops_commands(
    app: typer.Typer,
    *,
    state_store_fn: _StateStoreFactory,
    write_monitoring_snapshot_fn: _MonitoringSnapshotWriter,
    write_schedule_run_with_audit_fn: _ScheduleRunWriter,
    create_operation_manifest_fn: _OperationManifestBuilder,
    append_operation_manifest_fn: _OperationManifestAppender,
    refresh_execution_lineage_artifacts_fn: _ExecutionLineageRefresher,
    write_execution_read_only_surfaces_fn: _ExecutionReadOnlyWriter,
    daemon_dry_run_context_fn: _DaemonDryRunContextBuilder,
    write_daemon_manifest_artifacts_fn: _DaemonManifestArtifactsWriter,
    write_state_export_artifacts_fn: _StateArtifactsWriter,
    write_state_restore_artifacts_fn: _StateRestoreArtifactsWriter,
    normalize_phase_gate_summary_fn: Callable[[dict], dict],
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
    echo_audit_summary_fn: Callable[[dict], None],
    echo_phase_gate_summary_fn: Callable[[dict], None],
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
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
        store = state_store_fn(settings.data_dir, state_path)
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
        echo_audit_summary_fn(health)
        echo_phase_gate_summary_fn(health)
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
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
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
        write_daemon_manifest_artifacts_fn(settings.data_dir)
        logger.info("written: {}", out)
        typer.echo(f"run_id={manifest.run_id}")
        typer.echo(f"mode={manifest.mode}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
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
        refresh_execution_lineage_artifacts_fn(settings.data_dir, only_if_sources_exist=True)
        write_execution_read_only_surfaces_fn(settings.data_dir, state_path=state_path)
        context = daemon_dry_run_context_fn(settings.data_dir)
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
            execution_summary=context["execution_summary"],
            execution_comparison_summary=context["execution_comparison_summary"],
            execution_diagnostics_summary=context["execution_diagnostics_summary"],
            execution_gap_history_summary=context["execution_gap_history_summary"],
            execution_state_comparison_summary=context["execution_state_comparison_summary"],
            execution_snapshot_drift_summary=context["execution_snapshot_drift_summary"],
            execution_drift_overview_summary=context["execution_drift_overview_summary"],
            readiness_summary=context["readiness_summary"],
        )
        logger.info("written: {}", result.schedule_path)
        logger.info("written: {}", result.daemon_manifest_path)
        logger.info("written: {}", result.dry_run_snapshot_path)
        logger.info("appended: {}", result.operation_chain_path)
        typer.echo(f"run_id={result.run_id}")
        typer.echo(f"status={result.status}")
        typer.echo(f"scheduled_for={result.scheduled_for}")
        typer.echo(f"operation_chain={result.operation_chain_path}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("daemon-run")
    def daemon_run_cmd(
        mode: str = typer.Option("paper", "--mode"),
        command: str = typer.Option("uv run sis paper-step", "--command"),
        every_minutes: int = typer.Option(30, "--every-minutes"),
        max_cycles: int = typer.Option(1, "--max-cycles", min=1),
        forever: bool = typer.Option(False, "--forever", help="Run until kill-switch or command failure."),
        sleep_seconds: float | None = typer.Option(
            None,
            "--sleep-seconds",
            help="Override sleep between cycles. Useful for bounded local smoke runs.",
        ),
        state_path: Path | None = typer.Option(
            None,
            "--state-path",
            help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
        ),
    ) -> None:
        settings = get_settings()
        result = run_daemon_loop(
            data_dir=settings.data_dir,
            mode=mode,
            command=command,
            state_store_path=state_path or (settings.data_dir / "state/marketlens.sqlite"),
            every_minutes=every_minutes,
            kill_switch=KillSwitch(settings.data_dir / "state/kill_switch.flag"),
            max_cycles=None if forever else max_cycles,
            sleep_seconds=sleep_seconds,
        )
        write_daemon_manifest_artifacts_fn(settings.data_dir)
        daemon_loop_report = settings.data_dir / "reports/daemon_loop.md"
        daemon_loop_summary = settings.data_dir / "ops/daemon_loop_summary.json"
        snapshot_payload = read_json(result.loop_snapshot_path)
        snapshot_dict = snapshot_payload if isinstance(snapshot_payload, dict) else {}
        build_daemon_loop_report(
            snapshot=snapshot_dict,
            snapshot_path=str(result.loop_snapshot_path),
            event_log_path=str(result.event_log_path),
            out_path=daemon_loop_report,
            summary_path=daemon_loop_summary,
        )
        logger.info("written: {}", result.daemon_manifest_path)
        logger.info("written: {}", result.event_log_path)
        logger.info("written: {}", result.loop_snapshot_path)
        logger.info("written: {}", daemon_loop_report)
        logger.info("written: {}", daemon_loop_summary)
        logger.info("appended: {}", result.operation_chain_path)
        typer.echo(f"run_id={result.run_id}")
        typer.echo(f"status={result.status}")
        typer.echo(f"cycles_requested={result.cycles_requested}")
        typer.echo(f"cycles_completed={result.cycles_completed}")
        typer.echo(f"daemon_loop_path={result.loop_snapshot_path}")
        typer.echo(f"daemon_loop_report_path={daemon_loop_report}")
        typer.echo(f"daemon_loop_summary_path={daemon_loop_summary}")
        typer.echo(f"daemon_loop_events_path={result.event_log_path}")
        typer.echo(f"operation_chain={result.operation_chain_path}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
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
        store = state_store_fn(settings.data_dir, state_path)
        out = export_state_snapshot(store, settings.data_dir / "state/state_snapshot.json")
        logger.info("written: {}", out)
        typer.echo(str(out))
        payload = read_json(out)
        if isinstance(payload, dict):
            write_state_export_artifacts_fn(settings.data_dir, state_store_path=store.path)
            audit = payload.get("audit_summary")
            if isinstance(audit, dict):
                echo_audit_summary_fn(audit)
            phase_gate = payload.get("phase_gate_summary")
            if isinstance(phase_gate, dict):
                echo_phase_gate_summary_fn(normalize_phase_gate_summary_fn(phase_gate))
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
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
        store = state_store_fn(settings.data_dir, state_path)
        restore_state_snapshot(store, snapshot_path)
        payload = read_json(snapshot_path)
        if isinstance(payload, dict):
            write_state_restore_artifacts_fn(
                settings.data_dir,
                snapshot_path=snapshot_path,
                state_store_path=store.path,
                restored=True,
            )
        typer.echo("restored=true")
        if isinstance(payload, dict):
            audit = payload.get("audit_summary")
            if isinstance(audit, dict):
                echo_audit_summary_fn(audit)
            phase_gate = payload.get("phase_gate_summary")
            if isinstance(phase_gate, dict):
                echo_phase_gate_summary_fn(normalize_phase_gate_summary_fn(phase_gate))
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

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

    @app.command("monitoring-status")
    def monitoring_status_cmd(
        state_path: Path | None = typer.Option(
            None,
            "--state-path",
            help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
        ),
    ) -> None:
        settings = get_settings()
        out, snapshot = write_monitoring_snapshot_fn(settings.data_dir, state_path)
        logger.info("written: {}", out)
        typer.echo(f"status={snapshot['status']}")
        typer.echo(f"decision_summary_exists={snapshot['decision_summary_exists']}")
        typer.echo(f"weekly_review_exists={snapshot['weekly_review_exists']}")
        typer.echo(f"daily_pnl_exists={snapshot['daily_pnl_exists']}")
        typer.echo(f"operation_chain_exists={snapshot['operation_chain_exists']}")
        echo_audit_summary_fn(snapshot)
        echo_phase_gate_summary_fn(snapshot)
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
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
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
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
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
        run, out = write_schedule_run_with_audit_fn(
            settings.data_dir,
            run_type=run_type,
            command=command,
            at=at,
            every_minutes=every_minutes,
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
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
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
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("notification-outbox")
    def notification_outbox_cmd(
        level: str = typer.Option(..., "--level"),
        title: str = typer.Option(..., "--title"),
        body: str = typer.Option(..., "--body"),
        source: str = typer.Option("codex", "--source"),
        sink: str = typer.Option("local_outbox", "--sink"),
    ) -> None:
        settings = get_settings()
        outbox_path = settings.data_dir / "notifications/outbox.jsonl"
        latest_path = settings.data_dir / "notifications/latest_notification.json"
        record = queue_notification(
            outbox_path=outbox_path,
            latest_path=latest_path,
            level=level,
            title=title,
            body=body,
            source=source,
            sink=sink,
        )
        operation = create_operation_manifest_fn(
            operation="notification_outbox",
            mode="ops",
            command=shlex.join(
                [
                    "uv",
                    "run",
                    "sis",
                    "notification-outbox",
                    "--level",
                    level,
                    "--title",
                    title,
                    "--body",
                    body,
                    "--source",
                    source,
                    "--sink",
                    sink,
                ]
            ),
            status=str(record["status"]),
            artifacts=[str(outbox_path), str(latest_path)],
            notes=[
                f"notification_id={record['notification_id']}",
                f"sink={sink}",
                f"level={level}",
            ],
        )
        operation_chain_path = append_operation_manifest_fn(settings.data_dir / "ops/operation_manifests.jsonl", operation)
        report_path = settings.data_dir / "reports/notification_outbox.md"
        summary_path = settings.data_dir / "ops/notification_outbox_summary.json"
        build_notification_outbox_report(
            record=record,
            outbox_path=str(outbox_path),
            latest_path=str(latest_path),
            operation_chain_path=str(operation_chain_path),
            out_path=report_path,
            summary_path=summary_path,
        )
        logger.info("written: {}", outbox_path)
        logger.info("written: {}", latest_path)
        logger.info("written: {}", report_path)
        logger.info("written: {}", summary_path)
        logger.info("appended: {}", operation_chain_path)
        typer.echo(f"notification_id={record['notification_id']}")
        typer.echo(f"status={record['status']}")
        typer.echo(f"sink={record['sink']}")
        typer.echo(f"outbox_path={outbox_path}")
        typer.echo(f"latest_path={latest_path}")
        typer.echo(f"notification_outbox_report_path={report_path}")
        typer.echo(f"notification_outbox_summary_path={summary_path}")
        typer.echo(f"operation_chain={operation_chain_path}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
