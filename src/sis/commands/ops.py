from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

import typer
from loguru import logger

from sis.ops.daily_loss_limit import evaluate_daily_loss_limit, evaluate_max_exposure
from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.reports.ops_command_status import build_healthcheck_report, build_kill_switch_report
from sis.settings import get_settings
from sis.state.store import StateStore


class _StateStoreFactory(Protocol):
    def __call__(self, settings_data_dir: Path, state_path: Path | None) -> StateStore: ...


class _MonitoringSnapshotWriter(Protocol):
    def __call__(self, settings_data_dir: Path, state_path: Path | None) -> tuple[Path, dict]: ...


def register_ops_commands(
    app: typer.Typer,
    *,
    state_store_fn: _StateStoreFactory,
    write_monitoring_snapshot_fn: _MonitoringSnapshotWriter,
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
